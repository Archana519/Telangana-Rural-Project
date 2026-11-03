> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Data sources and licences (as recorded in the project; not re-verified)

| Dataset | Source | Licence status |
|---|---|---|
| Village boundary | TGRAC `AdministrativeInfoSystem_Folder/Administrative_Information_System/MapServer/27` (Village=DAMARAKUNTA, Mandal=MARKOOK, District=SIDDIPET); stored response declares EPSG:32644 | Not stated; not verified |
| Road network | TGRAC `SchoolGIS_Folder/Schools/MapServer/20` | Not stated; completeness/currentness unverified |
| Facilities / schools / health | TGRAC layers (school, health; the anganwadi record is excluded, see EXCLUSIONS.md) | Not stated |
| Land cover | ESA WorldCover 2021 v200 (10 m); version not stored in the raster | CC BY 4.0 (per project notes) |
| DEM | clipped file `damarakunta_dem_30m.tif`; file name `n17_e078_1arc_v3` suggests an SRTM-type product; source not recorded | Not verified |
| Imagery | Esri World Imagery 0.6 m mosaic (built 4 Oct 2026 from 11 `MapServer/export` requests); capture date 29 Apr 2026 at one sampled point (Esri identify result), elsewhere not recorded | Esri licence unresolved; the enquiry draft has NOT been sent; do not redistribute |
| Building candidates | `results/v8_instances/buildings_v8_full.gpkg` (model-derived) | Derived from imagery of unresolved licence |
| Cadastral | `reference/damarakunta_cadastral*.gpkg` (794 parcels) | Source and licence not re-checked |
| Google Open Buildings v3 (verification reference) | `reference/external/google_open_buildings_v3.gpkg` (1,537 polygons in the boundary) | CC BY 4.0 / ODbL per Google; not re-checked |
| LoveDA benchmark | Zenodo 10.5281/zenodo.5706578; arXiv 2110.08733 | CC BY 4.0 per the Zenodo record |

See also `inputs/METADATA.md`.
