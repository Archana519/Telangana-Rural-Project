#!/usr/bin/env python
"""Backward-compatible name: the Adilabad map series. The generic script is scripts/make_village_map_series.py (`--village adilabad_urban | aswaraopeta`)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("make_village_map_series", Path(__file__).with_name("make_village_map_series.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main()
