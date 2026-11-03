# Telangana Rural Roads Project

Planning shared village roads from satellite images and terrain data, so fewer metres of road are needed to reach every house.

Case study: **Damarakunta village**, Markook mandal, Siddipet district, Telangana.

> These are planning ideas on a map, not surveyed roads. Costs are rough planning figures, not rupee estimates.

---

## The idea in 30 seconds

1. Find the buildings in a satellite image.
2. Build a simple map of the village: land type, slope, and areas where roads cannot go.
3. For each house, find a cheap way to reach the road. Let nearby houses **share** the same path.
4. Compare with giving every house its own separate road.

**What we found:** one shared network is about **25% shorter** (5,069 m instead of 6,753 m) for 163 houses.

---

## I just want to...

| I want to... | Go here |
|---|---|
| See the final maps | `DELIVERABLES_DAMARAKUNTA_STAGE_B/02_FINAL_MAPS/` |
| See the result tables and charts | `DELIVERABLES_DAMARAKUNTA_STAGE_B/03_RESULTS_TABLES/` |
| Read the short project summary | `DELIVERABLES_DAMARAKUNTA_STAGE_B/00_START_HERE/README_PROJECT_OVERVIEW.md` |
| Read the thesis report | `Phase1_Report_CBIT_Format/` (PDF or Word file) |
| Open the review slides | `Presentation_Review/MTech_Major_Project_Review.pptx` |
| See what is finished and what is still open | `DELIVERABLES_DAMARAKUNTA_STAGE_B/00_START_HERE/COMPLETION_GATE.md` |
| Trace building roofs by hand | `digitizer/README.md` |
| Check where the data came from | `inputs/METADATA.md` and `docs/data/DATA_SOURCES.md` |
| Run the whole thing again | see **Run it yourself** below |

---

## What is in each folder

| Folder | In plain words |
|---|---|
| `DELIVERABLES_DAMARAKUNTA_STAGE_B/` | The finished results: maps, tables, checks. Start with `00_START_HERE`. |
| `Phase1_Report_CBIT_Format/` | The written report and the tools that build it. |
| `Presentation_Review/` | The slide deck. |
| `scripts/` | The verified working scripts. Hash-checked, so please do not move them (see `scripts/README.md`). |
| `src/` | Newer helper code: the pipeline, reports, extra checks. Safe to change. |
| `digitizer/` | A small app for tracing roofs in your browser. |
| `configs/`, `inputs/` | Settings and notes about the input data. |
| `docs/` | Status, plans, data notes and decisions (see `docs/README.md`). |
| `Siddipet/Damarakunta/` | The village data the pipeline reads. |
| `outputs/` | Created when you run the tool. Not stored in Git. |

### Inside `src/`

| Folder | What it does |
|---|---|
| `run_pipeline.py`, `run_final_package.py` | The two big steps (`telangana run`, `telangana package`). |
| `telangana_cli.py` | The `telangana` command. |
| `routing/` | Explains why each route was chosen. |
| `validation/` | Extra checks on detection, facilities and connectivity. |
| `reporting/` | Maps, charts, tables and the thesis chapter. |
| `modeling/`, `preprocessing/` | Model training and road clipping. |

---

## Run it yourself

One-time setup (from the project folder):

```bash
pip install -e .
```

After that, the `telangana` command works from **any folder**:

```bash
telangana run --dry-run      # check everything first, runs nothing
telangana run                # quick run
telangana run --profile full # full run
telangana package            # build the final maps and tables
telangana latest             # show where the newest results are
telangana open               # open the newest results folder
telangana clean              # remove old runs, keep the newest 3
```

Each run is saved in its own folder, `outputs/run_<date>_<time>/`. After every run the tool points `outputs/latest` at the newest one and **deletes older runs beyond the newest 3**, so results do not pile up. Change that with `--keep 5`, or switch it off with `--no-clean`. The reference run is never deleted.

### What the results look like

Every run gets its own dated folder, so runs never mix:

```
outputs/
├── INDEX.md                      <- all saved runs, newest first, with date and PASS/FAILED
├── latest/                       <- shortcut to the newest run
└── run_20261103_195802/          <- one run (3 Nov 2026, 19:58)
    ├── RUN_SUMMARY.md            <- read this first: date, result, what is where
    ├── 1_buildings/              <- building footprints, facilities
    ├── 2_terrain/                <- cost map, existing roads
    ├── 3_routes/                 <- new routes and why each was chosen
    ├── 4_what_if_tests/          <- stress-test results
    ├── 5_checks/                 <- validation and connectivity checks
    └── pipeline.log              <- full log
```

**In VS Code:** press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`), choose **Tasks: Run Task**, and pick a `Telangana: ...` item. No typing needed.

**Results are never pushed to Git.** The `outputs/` folder and the per-run folders are ignored, so running many times never clutters the repo.

You also need the original data files on your computer (they are not stored here), plus Python packages `rasterio`, `geopandas`, `shapely`, `numpy`, `networkx`.

---

## Please keep in mind

- No field visit has confirmed any route.
- The satellite image licence is not settled yet.
- Some result files were rebuilt after the originals were lost. The result tables are the source of truth.

Questions about the project? Start with `docs/status/PROJECT_COMPLETION_STATUS.md`.
