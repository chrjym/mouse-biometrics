# Seed 945, split 1_5 (1 legitimate user, 5 impostors)

Record of the 1_5 runs on seed 945, copied from the git-ignored `runs/19399f/1_5_*/`
(created 2026-10-26, code at commit 8ee4f2069). Only the 1_5 split is kept here.

- Legitimate user: user29. Impostors: user15, user20, user23, user35, user9.
- Strokes: a pause > 0.5 s (`pause_gap_s: 0.5`) or a click starts a new stroke; strokes with < 10 points dropped.
- Matching: resample 64 points, DTW band 0.1, shape ratio 0.2, session ratio 0.5.
- `labels_file: datasets/balabit/public_labels.csv` is set, so sessions marked `is_illegal=1` were left out
  (`src/00_config.py`). The current main config uses no label file.

`summary.csv` has one row per run. The per-run files stay in `runs/19399f/1_5_*/`.

## Results

Rejecting everyone scores 5/6 = 0.83, so 0.83 means no separation.

| Sensitivity | Sessions | User accuracy | Legit through | Impostors through |
|---|---|---|---|---|
| 0.01–0.04 | 1 | 0.83 | 0/1 | 0/5 |
| **0.05** | **1** | **1.00** | **1/1** | **0/5** |
| 0.06 | 1 | 0.67 | 1/1 | 2/5 |
| 0.05 | 5–40 | 0.17 | 1/1 | 5/5 |

Sensitivity 0.05 with 1 session is the only setting that separates the users. It does not hold on the
other 1_5 seeds (948: 0.50, 949: 0.83, 950: 0.50 at the same setting), so it is a best case, not a general result.
