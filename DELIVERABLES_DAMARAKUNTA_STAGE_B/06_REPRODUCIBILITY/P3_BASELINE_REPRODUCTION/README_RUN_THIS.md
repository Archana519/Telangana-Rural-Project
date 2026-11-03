> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# P3 baseline reproduction

Original run: `stageB/S2_fac_C0_s25_P3_none` (runner `dk_stageB_run v1.2`). Recorded result: 163 houses, house unique length 4761.726 m, combined unique ordinal cost 21560.633.

**Status (reconstruction): PARTIAL.** Every pipeline run regenerates the P3 run and its lengths and costs match the reference exactly (checked in three fresh runs). A route-level geometry comparison (`dk_stageB_run_repro_compare_v1.py`) was done for the primary run only. To complete it:

```bash
python scripts/dk_stageB_run_repro_compare_v1.py --original <reference stageB>/S2_fac_C0_s25_P3_none --repro <new stageB>/S2_fac_C0_s25_P3_none --out <new stageB>/_compare_P3
```
