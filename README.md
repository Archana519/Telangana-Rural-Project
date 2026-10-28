# Siddipet scripts (Angadi Kistapur first)

All scripts are read-only towards TGRAC and never overwrite earlier raw files
(every output name carries a UTC time stamp). Run them from this `scripts` folder.

## One-time setup (Windows, VS Code terminal, PowerShell)

    cd D:\Telangana_Rural_Project\scripts
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Order

1. `python verify_siddipet_village.py`
2. `python inspect_tgrac_angadi_kistapur.py`
3. `python inspect_geotiff.py <image.tif>` (only once you legally hold an image)
4. `python prepare_siddipet_village.py --boundary <boundary file> [--tgrac-layer NAME=URL/<id>] [--dem <srtm.tif>]`

Add `--insecure` only if a TGRAC request fails with an SSL certificate error.
TGRAC may not answer outside India; run from an Indian network.

## Rules kept by these scripts
- CRS and transform always come from the data; the LoveDA 0.55 m/pixel factor is never used.
- No imagery is exported or downloaded from TGRAC by any script.
- `raw/` = as received; `reference/` = clipped copies; `aligned/` = village UTM.
- `technical_verification_loveda/` stays a separate folder at project root.
