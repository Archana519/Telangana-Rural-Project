# 01_ADILABAD: Tier 1, urban / peri-urban (Adilabad Urban mandal, 17.75 km2)

Start with `00_DATA_SOURCE_AUDIT.md` (study window, every input with endpoint, licence and SHA-256, the facility verification, why open footprints replace StrongDINOv2Seg, and every deviation from Stage B).

| File | Content |
|---|---|
| `00_DATA_SOURCE_AUDIT.md` | data-source audit and deviations from Damarakunta |
| `input_manifest.csv` | one row per input layer: URL / endpoint, release, licence, resolution, SHA-256, bytes, rows |
| `verified_facilities.csv` | every school / health / government candidate in the window with coordinates, distance to the nearest footprint and road, status and exclusion reason |
| `building_extraction_summary.csv` | footprint counts and median area by source and quality class |
| `routing_strategy_comparison.csv` | straight line, independent least-cost, length-only control, roads-only shared reference, two-stage shared plan |
| `penalty_sensitivity.csv` | mu = 1, 4, 20, 100 (cell-centre rule) and buffered 7.1 m footprints with mu = 20, 100 |
| `omission_runs.csv`, `omission_summary.csv` | 10% / 20% random omission (5 seeds each) and smallest 10% / 25% |
| `target_definition_sensitivity.csv` | road-gap threshold 20 / 30 / 50 m |
| `comparison_vs_damarakunta.md` / `.csv` | side-by-side with the Phase 1 / Stage B results |
| `figures/map1_study_area.png` | boundary, roads, buildings, facilities, land-cover context, zoom |
| `figures/map2_network_comparison.png` | independent vs shared network, full window and zoom, with lengths and costs |
| `figures/fig3_sensitivity.png` | penalty trade-off and omission sensitivity |

Reproduce (about 40 minutes on 4 cores; the raw data are re-downloaded, nothing is committed except these deliverables):

```
python -m src.multivillage.run --village adilabad_urban --steps acquire prepare extract
python -m src.multivillage.run --village adilabad_urban --steps route --workers 4
python -m src.multivillage.report --village adilabad_urban
```
