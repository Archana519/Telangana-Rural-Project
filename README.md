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
| Check where the data came from | `inputs/METADATA.md` and `docs/DATA_SOURCES.md` |
| Run the whole thing again | see **Run it yourself** below |

---

## What is in each folder

| Folder | In plain words |
|---|---|
| `DELIVERABLES_DAMARAKUNTA_STAGE_B/` | The finished results: maps, tables, checks. Start with `00_START_HERE`. |
| `Phase1_Report_CBIT_Format/` | The written report. |
| `Presentation_Review/` | The slide deck. |
| `src/` | The code that does the work (see below). |
| `scripts/` | Older copies of the same code. Keep them for now; the runner still looks here. |
| `digitizer/` | A small app for tracing roofs in your browser. |
| `configs/`, `inputs/` | Settings and notes about the input data. |
| `docs/` | Background notes, decisions and project status. |
| `Siddipet/` | Village data and earlier work. Mostly for reference. |
| `outputs/` | Files made by earlier runs. |

### Inside `src/`

| Folder | What it does |
|---|---|
| `preprocessing/` | Prepares the village map (boundary, land type, slope, cost). |
| `modeling/` | Finds buildings in the satellite image. |
| `routing/` | Plans the shared road network. |
| `stress_test/` | Asks "what if some buildings are missing or extra?" |
| `validation/` | Checks that the results are sound and connected. |
| `reporting/` | Draws the maps and charts. |

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
telangana clean              # remove old runs, keep the newest 3
```

Each run is saved in its own folder, `outputs/run_<date>_<time>/`. After every run the tool points `outputs/latest` at the newest one and **deletes older runs beyond the newest 3**, so results do not pile up. Change that with `--keep 5`, or switch it off with `--no-clean`. The reference run is never deleted.

You also need the original data files on your computer (they are not stored here), plus Python packages `rasterio`, `geopandas`, `shapely`, `numpy`, `networkx`.

---

## Please keep in mind

- No field visit has confirmed any route.
- The satellite image licence is not settled yet.
- Some result files were rebuilt after the originals were lost. The result tables are the source of truth.

Questions about the project? Start with `docs/PROJECT_COMPLETION_STATUS.md`.
