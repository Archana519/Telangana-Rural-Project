# Reproduce

Snapshot copies: these files are copied at build time and will differ from `docs/results/` after the next audit run (the audit stamps the git commit).
The audit itself checks `docs/results/`, not these copies.

```bash
pip install -r requirements.txt
python -m src.utils.data_downloader_helper --levels gp mandal district --overture-release 2026-10-21.0
python -m src.routing.run_hierarchy --levels 2 3 4 --data real --out docs/results/hierarchy_real_run     # seeds 11, 12, 13 (configs/hierarchy_levels.yaml)
python -m src.evaluation.penalty_sweep
python -m src.evaluation.plot_hierarchy_figures
python -m src.evaluation.plot_level1_omission
python -m src.evaluation.provenance_audit --write docs/results/PROVENANCE_AND_PROOFS.md --rerun --redownload
python -m src.evaluation.build_contribution3_deliverables
python -m pytest
python paper/build_docx.py
```
