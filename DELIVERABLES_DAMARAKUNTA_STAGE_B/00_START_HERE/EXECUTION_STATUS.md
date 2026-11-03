> **RECONSTRUCTION (2026-11-02).** The original deliverables folder was lost and was not under version control. This file was rebuilt from the live result files and from the original text as displayed earlier in the same working session, and updated where later evidence changed it. It is not the original file.

# Execution status

| Stage | Status | Evidence |
|---|---|---|
| 1 Detect (building candidates, facilities) | Reused input, verified by hash; detections unverified | `inputs/METADATA.md`, `outputs/verification/` |
| 2 Model terrain (10 m grid, cost surface) | Verified input | `04_VALIDATION/INPUT_OUTPUT_MANIFESTS/` |
| 3 Plan (Stage A alternatives, Stage B selection) | Run and reproduced exactly in fresh runs (27 reference runs, 405 metrics identical) | `outputs/run_*/RUN_SUMMARY.md` |
| 4 Stress-test (C1 omit/add, C2 ablation) | Run; C1 perturbations are synthetic | `03_RESULTS_TABLES/` |
| 5 Validate and report | Run; connectivity audit v2 lists house C0002 as a failure, the acceptance validator as information | `03_RESULTS_TABLES/CONNECTIVITY/`, `04_VALIDATION/` |
| Building-avoiding scenario (runner v1.4) | Run; crossings reduced, not eliminated (counts in table6_obstacle_avoidance.csv) | `outputs/final_comparison/table6_obstacle_avoidance.csv` |
| Visual audit of facilities | Protocol and table prepared; observation columns empty | `outputs/visual_audit/` |
| C3 transfer | Not started; blocked on written approval of the gate | `COMPLETION_GATE.md` |
