"""READ-ONLY: what do the raw LoveDA mask IDs mean? (the training data itself, not code)
For Train/Val x Urban/Rural it prints the share of each raw ID over ALL masks (not a sample), and writes ONE
contact sheet PNG (new folder) showing real images with ID 2 in red, ID 3 in yellow, ID 4 in blue so you can
SEE which ID sits on roofs. Reads dataset files only; writes only the PNG + CSV in results\\mapping_audit.
  python scripts\\audit_loveda_masks.py [--data "<LoveDA root>"] [--tiles 4]
"""
import argparse, csv, os, sys
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("--data", default=r"D:\new_MPS\remoteSensingWebApp\LoveDA Satellite Images Semantic Segmentation")
ap.add_argument("--out", default=r"D:\Telangana_Rural_Project\Siddipet\Damarakunta\results\mapping_audit")
ap.add_argument("--tiles", type=int, default=4, help="(legacy) used only when --ids is not given")
ap.add_argument("--group", default=None, help="e.g. Train/Rural, Val/Rural (default: Train/Urban)")
ap.add_argument("--ids", default=None, help="comma list of raw IDs to highlight, e.g. 0,5,6,7. For each ID the tiles with the LARGEST share of it are shown")
ap.add_argument("--per-id", type=int, default=2)
a = ap.parse_args()

groups = {}
for split in ("Train", "Val"):
    for dom in ("Urban", "Rural"):
        d = os.path.join(a.data, split, split, dom, "masks_png")
        if os.path.isdir(d):
            groups[f"{split}/{dom}"] = d
if not groups:
    sys.exit(f"no masks_png folders found under {a.data}")

os.makedirs(a.out, exist_ok=True)
rows = []
perfile = {}
print("Share of pixels per RAW mask ID (%), over every mask in the folder:")
print("group".ljust(12), "n_masks".rjust(8), *[f"ID{k}".rjust(7) for k in range(8)])
for g, d in groups.items():
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".png"))
    tot = np.zeros(256, np.int64)
    perfile[g] = {}
    for f in files:
        c = np.bincount(np.asarray(Image.open(os.path.join(d, f))).ravel(), minlength=256)
        perfile[g][f] = c[:8] / max(c.sum(), 1)
        tot += c
    s = tot.sum()
    other = int(tot[8:].sum())
    pct = [100 * tot[k] / s for k in range(8)]
    print(g.ljust(12), str(len(files)).rjust(8), *[f"{p:7.2f}" for p in pct], ("" if other == 0 else f"  (!) {other} px with ID>=8"))
    rows.append([g, len(files)] + [int(tot[k]) for k in range(8)] + [other])
with open(os.path.join(a.out, "loveda_mask_id_counts.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["group", "n_masks"] + [f"id{k}" for k in range(8)] + ["id_ge8"]); w.writerows(rows)

# contact sheet
COL = {0: (255, 0, 255), 2: (255, 0, 0), 3: (255, 255, 0), 4: (0, 120, 255), 5: (255, 140, 0), 6: (0, 90, 0), 7: (120, 255, 60)}
NAME = {0: "ID0 magenta", 2: "ID2 red", 3: "ID3 yellow", 4: "ID4 blue", 5: "ID5 orange", 6: "ID6 dark green", 7: "ID7 lime"}
from PIL import ImageDraw
pick = a.group or next((g for g in ("Train/Urban", "Train/Rural", "Val/Urban", "Val/Rural") if g in groups), None)
if pick not in groups:
    sys.exit(f"group {pick} not found; have {list(groups)}")
d = groups[pick]
imgdir = os.path.join(os.path.dirname(d), "images_png")
files = sorted(perfile[pick])
ids = [int(x) for x in a.ids.split(",")] if a.ids else [2, 3, 4]
chosen = []                       # (tile, id it was chosen for)
if a.ids:
    for k in ids:
        for f in sorted(files, key=lambda f: -perfile[pick][f][k])[:a.per_id]:
            chosen.append((f, k))
else:
    chosen = [(files[i], None) for i in np.linspace(0, len(files) - 1, a.tiles).astype(int)]
S = 384
sheet = []
for f, k in chosen:
    m = np.asarray(Image.open(os.path.join(d, f)))
    ip = os.path.join(imgdir, f)
    if not os.path.exists(ip):
        print("image not found for", f, "(looked in", imgdir + ")"); continue
    im = np.asarray(Image.open(ip).convert("RGB")).copy()
    ov = im.copy()
    for kk in ids:
        sel = m == kk
        if sel.any():
            ov[sel] = (0.35 * ov[sel] + 0.65 * np.array(COL[kk])).astype(np.uint8)
    A = Image.fromarray(im).resize((S, S)); B = Image.fromarray(ov).resize((S, S))
    dr = ImageDraw.Draw(B)
    share = ", ".join(f"ID{kk} {100 * perfile[pick][f][kk]:.0f}%" for kk in ids)
    dr.rectangle([0, 0, S, 16], fill=(0, 0, 0)); dr.text((3, 2), f"{pick}/{f}  {share}", fill=(255, 255, 255))
    sheet.append(np.hstack([np.asarray(A), np.asarray(B)]))
if sheet:
    tag = pick.replace("/", "_") + ("_ids" + a.ids.replace(",", "") if a.ids else "")
    p = os.path.join(a.out, f"mask_id_contact_sheet_{tag}.png")
    Image.fromarray(np.vstack(sheet)).save(p)
    print(f"\nContact sheet ({pick}; left = image, right = overlay of " + ", ".join(NAME[k] for k in ids if k in NAME) + f"): {p}")
print("Judge by eye: does each colour sit on the thing the LoveDA legend says (2 building, 3 road, 4 water, 5 barren, 6 forest, 7 agricultural, 0 no-data)?")