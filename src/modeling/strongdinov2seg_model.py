"""StrongDINOv2Seg architecture, importable without running the training loop.

Verbatim copy of the model classes (ResidualConvBlock, ASPP, FPNFuse, StrongDINOv2Seg) from src/modeling/strongdinov2seg_training_updated.py
(the training notebook export; that file runs training at import time, so it cannot be imported). Only `cfg.NUM_CLASSES` became the constant below.
The Damarakunta inference (scripts/run_tiled_inference.py) imported the same class from D:\\new_MPS\\remoteSensingWebApp\\project\\model.py, which is outside
this repository; run_adilabad_end_to_end.py prefers that file when it exists and falls back to this copy, and in both cases requires
load_state_dict(strict=False) to report NO missing keys, so a mismatching architecture fails loudly instead of silently.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModel

NUM_CLASSES = 8   # LoveDA ids 0..7 (0 = ignore)


class ResidualConvBlock(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch,  out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
        )
        self.skip = (
            nn.Sequential(nn.Conv2d(in_ch, out_ch, 1, bias=False),
                          nn.BatchNorm2d(out_ch))
            if in_ch != out_ch else nn.Identity()
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.relu(self.conv(x) + self.skip(x))


class ASPP(nn.Module):
    def __init__(self, in_ch, out_ch, rates=(6, 12, 18)):
        super().__init__()
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True))
        self.dilated = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 3, padding=r, dilation=r, bias=False),
                nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True))
            for r in rates])
        self.pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_ch, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True))
        n = 1 + len(rates) + 1
        self.project = nn.Sequential(
            nn.Conv2d(out_ch * n, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Dropout2d(0.1))

    def forward(self, x):
        H, W = x.shape[-2:]
        out = [self.conv1(x)]
        for d in self.dilated:
            out.append(d(x))
        gp = F.interpolate(self.pool(x), size=(H, W),
                           mode="bilinear", align_corners=False)
        out.append(gp)
        return self.project(torch.cat(out, dim=1))


class FPNFuse(nn.Module):
    def __init__(self, encoder_dim=768, fpn_dim=256):
        super().__init__()
        self.lat = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(encoder_dim, fpn_dim, 1, bias=False),
                nn.BatchNorm2d(fpn_dim), nn.ReLU(inplace=True))
            for _ in range(4)])
        self.fuse = nn.Sequential(
            nn.Conv2d(fpn_dim * 4, fpn_dim * 2, 1, bias=False),
            nn.BatchNorm2d(fpn_dim * 2), nn.ReLU(inplace=True))

    def forward(self, feats):
        H, W = feats[0].shape[-2:]
        lats = []
        for i, f in enumerate(feats):
            l = self.lat[i](f)
            if l.shape[-2:] != (H, W):
                l = F.interpolate(l, size=(H, W),
                                  mode="bilinear", align_corners=False)
            lats.append(l)
        return self.fuse(torch.cat(lats, dim=1))


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL
# ══════════════════════════════════════════════════════════════════════════════
class StrongDINOv2Seg(nn.Module):
    def __init__(self):
        super().__init__()
        self.patch_size  = 14
        self.encoder_dim = 768

        self.encoder = AutoModel.from_pretrained(
            "facebook/dinov2-base",
            output_hidden_states=True)
        for p in self.encoder.parameters():
            p.requires_grad = True

        self.fpn  = FPNFuse(encoder_dim=768, fpn_dim=256)
        self.aspp = ASPP(in_ch=512, out_ch=256)

        self.up1  = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.dec1 = ResidualConvBlock(256, 256)
        self.up2  = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.dec2 = ResidualConvBlock(256, 128)
        self.up3  = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.dec3 = ResidualConvBlock(128,  64)
        self.up4  = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=False)
        self.dec4 = ResidualConvBlock( 64,  32)

        self.seg_head = nn.Conv2d(32, NUM_CLASSES, kernel_size=1)
        self.aux1     = nn.Conv2d(256, NUM_CLASSES, kernel_size=1)
        self.aux2     = nn.Conv2d(128, NUM_CLASSES, kernel_size=1)
        self.aux3     = nn.Conv2d(64,  NUM_CLASSES, kernel_size=1)

    def _to_map(self, hidden, H, W):
        x       = hidden[:, 1:, :]
        B, N, C = x.shape
        Hp      = H // self.patch_size
        Wp      = W // self.patch_size
        return x.permute(0, 2, 1).reshape(B, C, Hp, Wp)

    def forward(self, x):
        B, _, H, W = x.shape
        enc    = self.encoder(pixel_values=x, output_hidden_states=True)
        layers = enc.hidden_states

        f3  = self._to_map(layers[3],  H, W)
        f6  = self._to_map(layers[6],  H, W)
        f9  = self._to_map(layers[9],  H, W)
        f12 = self._to_map(layers[12], H, W)

        neck = self.aspp(self.fpn([f3, f6, f9, f12]))

        d1 = self.dec1(self.up1(neck))
        d2 = self.dec2(self.up2(d1))
        d3 = self.dec3(self.up3(d2))
        d4 = self.dec4(self.up4(d3))
        d4 = F.interpolate(d4, size=(H, W), mode="bilinear", align_corners=False)

        main = self.seg_head(d4)

        if self.training:
            a1 = F.interpolate(self.aux1(d1), size=(H, W),
                               mode="bilinear", align_corners=False)
            a2 = F.interpolate(self.aux2(d2), size=(H, W),
                               mode="bilinear", align_corners=False)
            a3 = F.interpolate(self.aux3(d3), size=(H, W),
                               mode="bilinear", align_corners=False)
            return main, a1, a2, a3

        return main
