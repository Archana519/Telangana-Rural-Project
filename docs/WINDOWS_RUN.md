# Running the pipeline on Windows (cmd.exe)

Run from the repository folder with the virtual environment active. One command per line.

```bat
git pull origin main
pip install -r requirements.txt
python -m src.utils.data_downloader_helper --plan
python -m src.utils.data_downloader_helper --levels gp mandal district --overture-release 2026-10-21.0
python -m src.utils.data_downloader_helper --plan
```
The download retries network errors by itself (up to 6 attempts per Overture read). If it still stops with an AWS network error, just
run the same command again: files already written are skipped and the run continues with what is missing.
Everything must show `[present]` before the next block.

```bat
python -m pytest -q
python -m src.evaluation.provenance_audit --rerun --redownload
```
Do NOT run `git add --renormalize .` and do not regenerate maps/figures just to "check" them: figures rendered on Windows differ
byte-for-byte from the committed ones (different fonts), which makes the manifest hash check fail. Regenerate them only when you
intend to commit new versions (`python -m src.evaluation.plot_hierarchy_figures`, `python -m src.evaluation.build_contribution3_deliverables`).

If generated files show as modified after a run and you want the committed versions back:
```bat
git restore DELIVERABLES_CONTRIBUTION_3_HIERARCHICAL_ROUTING docs/results paper/figures DELIVERABLES_DAMARAKUNTA_STAGE_B
```
