#!/usr/bin/env python
"""Inputs of the open-data Damarakunta run (config damarakunta_open): the same layers as Adilabad, Aswaraopeta and Alampur.

    python scripts/prepare_damarakunta_open_inputs.py

The study polygon, roads (Overture / OpenStreetMap), land cover (ESA WorldCover), elevation (Copernicus GLO-30) and facilities (OpenStreetMap, Overture, Wikidata, Wikipedia)
come from the open stages of the multi-village pipeline (`python -m src.multivillage.run --village damarakunta_open ...`). The building footprints are the StrongDINOv2Seg
instances of the Damarakunta mosaic that already exist (Siddipet/Damarakunta/results/v8_instances/buildings_v8_full.gpkg, read-only): they were produced from Esri imagery by the
same model and the same extraction code as the other three areas and do not depend on any TGRAC layer. This script only clips them to the open-data study polygon and writes the
copy that the pipeline expects (data/villages/damarakunta_esri/results/v8_instances/buildings_v8_damarakunta.gpkg). Nothing in DELIVERABLES_DAMARAKUNTA_STAGE_B/ or Siddipet/ is modified.
"""
from pathlib import Path

import geopandas as gpd

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "Siddipet" / "Damarakunta" / "results" / "v8_instances" / "buildings_v8_full.gpkg"
BOUNDARY = REPO / "data" / "villages" / "damarakunta_open" / "boundary.gpkg"
OUT = REPO / "data" / "villages" / "damarakunta_esri" / "results" / "v8_instances" / "buildings_v8_damarakunta.gpkg"


def main():
    poly = gpd.read_file(BOUNDARY).to_crs("EPSG:32644").geometry.union_all()
    b = gpd.read_file(SRC, layer="buildings").to_crs("EPSG:32644")
    b["inside_village"] = b.geometry.representative_point().within(poly)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    b.to_file(OUT, layer="buildings", driver="GPKG")
    for lay in ("components", "rejected"):
        try:
            gpd.read_file(SRC, layer=lay).to_crs("EPSG:32644").to_file(OUT, layer=lay, driver="GPKG")
        except Exception:
            pass
    print(f"{len(b)} instances ({int(b.inside_village.sum())} inside the open-data polygon) -> {OUT}")


if __name__ == "__main__":
    main()
