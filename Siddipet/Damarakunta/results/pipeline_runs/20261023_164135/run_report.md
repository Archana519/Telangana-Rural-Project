# Pipeline run 20261023_164135 - Damarakunta
Overall: **OK**

Outputs are UNVERIFIED model-derived candidates (not surveyed buildings, not construction-ready roads).

| stage | status | seconds |
|---|---|---|
| inference | ADOPTED_EXISTING_OUTPUTS |  |
| extract_buildings_v8 | ADOPTED_EXISTING_OUTPUTS |  |
| access | RAN_OK | 17.0 |
| network_planner | DISABLED |  |

## Warnings
- raster.blank: 3.32% of pixels are all-zero (no imagery). They are NOT land cover; extraction rejects building blobs on them.
- inference: outputs existed with no recorded provenance; hashed and recorded, NOT rerun
- extract_buildings_v8: outputs existed with no recorded provenance; hashed and recorded, NOT rerun