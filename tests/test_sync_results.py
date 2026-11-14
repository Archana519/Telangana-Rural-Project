import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("sync_results", Path(__file__).resolve().parents[1] / "scripts" / "sync_results_to_folder.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_sync_copies_all_deliverables_and_dry_run_writes_nothing(tmp_path):
    m.sync(tmp_path, dry_run=True, log=lambda *_: None)
    assert not (tmp_path / "contribution3").exists()
    m.sync(tmp_path, log=lambda *_: None)
    root = tmp_path / "contribution3"
    for rel in ("hierarchy_real_run/hierarchy_summary.csv", "hierarchy_real_run/gp/gp_routes.gpkg", "input_manifest.csv",
                "PROVENANCE_AND_PROOFS.md", "manuscript/manuscript.docx", "manuscript/main.tex", "manuscript/references.bib"):
        assert (root / rel).stat().st_size > 0, rel
