# Environmental Research Letters manuscript (single-column article layout)

`main.tex` is the ERL submission of the four-settlement study (Damarakunta, Adilabad, Aswaraopeta, Alampur). It is written by `build_main.py`
(prose in the script; numbers read from the committed result files through `src/multivillage/pipeline_summary.py`; the appendix strategy table is built from the committed routing_strategy_comparison.csv files).

```bash
python paper_erl/build_main.py                       # rewrites main.tex and refreshes the figure / table copies
cd paper_erl && pdflatex main && bibtex main && pdflatex main && pdflatex main
ERIS_TEX=paper_erl/main.tex python paper_eris/verify_eris_numbers.py     # ledger check of the numbers (ERL mode checks the four-area numbers; the ERIS manuscript keeps the 2018-mandal ledger)
```

Figures: `fig_architecture.png` (Figure 1; source `paper_erl/fig_architecture.tex`, synced to `paper_eris/`) and `fig_flow_study_areas.png` (Figure 2; regenerate on the PC that holds the segmentation results with
`python scripts/build_paper_flow_figure.py --source segmentation`). Table 3 is `paper_comparison_table.tex` (`python scripts/run_village_pipeline.py --compare-all`).
The manuscript uses the plain `article` class (A4, 1 in margins, one column) with no running header; `iopjournal.cls` and the IOP guideline files in this folder are kept only for reference. The CRediT roles are a draft to be confirmed by the authors.
`make_from_eris.py` is the earlier generator and is superseded by `build_main.py`.

Figures 3-6 (`fig_split1_footprints`, `fig_split2_cost_surface`, `fig_stage_AB`, `fig_shared_network_detail`) are multi-panel composites cropped from the committed map series of the four areas:
`python scripts/build_paper_result_figures.py`. Figure 1 is the two-split architecture (`fig_architecture.tex`, synced to `paper_eris/`).

## Damarakunta: open-data run (identical inputs for all four windows)
Damarakunta is processed from the same open layers as the other three windows (config `configs/multivillage/villages/damarakunta_open.yaml`; no TGRAC layer):
```bash
python scripts/propose_aoi.py --village damarakunta_open --sources --settlement-extent --extent-from buildings --centre 17.7073 78.7519 --pick 0   # window from Overture footprints
python -m src.multivillage.run --village damarakunta_open --steps acquire prepare --skip-buildings                                              # Overture / OSM roads, WorldCover, Copernicus DEM
python scripts/prepare_damarakunta_open_inputs.py                                                                                               # clip the existing StrongDINOv2Seg footprints to the window
python scripts/audit_facilities.py --village damarakunta_open --footprints data/villages/damarakunta_esri/results/v8_instances/buildings_v8_damarakunta.gpkg
python scripts/run_village_end_to_end.py --village damarakunta_open --stage route --quick --workers 2
python scripts/run_village_end_to_end.py --village damarakunta_open --stage report --quick
python scripts/make_village_map_series.py --village damarakunta_open --esri-service
python scripts/run_village_pipeline.py --compare-all && python scripts/build_paper_result_figures.py && python paper_erl/build_main.py
```
The StrongDINOv2Seg inference itself was not re-run (no PyTorch or checkpoint in the cloud container): the footprints are the existing instances of the same checkpoint and extraction code, which do not depend on TGRAC.
