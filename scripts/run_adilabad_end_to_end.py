#!/usr/bin/env python
"""Backward-compatible name: the Adilabad end-to-end run. The generic script is scripts/run_village_end_to_end.py (`--village adilabad_urban | aswaraopeta`)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("run_village_end_to_end", Path(__file__).with_name("run_village_end_to_end.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})

if __name__ == "__main__":
    _mod.main(default_village="adilabad_urban")
