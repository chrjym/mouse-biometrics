# Script documentation (`experiment_earl/src/`)

One page per script: what it does, the algorithm step by step, the formulas it uses, and why we chose that
algorithm or formula. Setting names in `code` are keys of [`config.yaml`](../config.yaml) (all explained in
[`CONFIG.md`](../CONFIG.md)); how to run each script is in [`README.md`](../README.md); how to read the figures is in [`READING_FIGURES.md`](../READING_FIGURES.md).
Each page ends with its own **References** (IEEE style, with DOI or link); all of them are collected in
[REFERENCES.md](REFERENCES.md).

## The pipeline at a glance

```
                          00_config  (settings, run folders, session loader, used by every script)
                              │
   ┌──────────────────────────┼─────────────────────────────────────────────────────────────┐
   │ A. Shape matching (does an impostor's stroke look like one of the user's strokes?)       │
   │   01 draw users → 02 draw sessions → 03 cut into strokes → 04 DTW match → 05 sensitivity │
   │   06 draw the strokes   07 run the notebook   08 draw matched pairs   09 genuine check   │
   │   10 accuracy per user across the runs of one hash folder                               │
   │   12 best sensitivity and sessions per split (from 10's accuracy.csv)                   │
   │   13 cohort scoring: closer to the claimed user than to other people? (EER vs 12)       │
   │   14 new-seed check: 12's and 13's chosen settings, unchanged, on new seeds             │
   │   15 draw 13's scoring: strokes vs nearest strokes per library; scores per split        │
   │   16 sensitivity sweep: fixed splits × library size × sensitivity → confusion matrices  │
   │   17 draw 16's sweep: accuracy vs sensitivity, heatmap, FAR/FRR                        │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
```

| Script | Page | Algorithm in one line |
|---|---|---|
| 00 | [00_config.md](00_config.md) | Config loading, SHA-1 run folders, seeded session order, cleaning raw Balabit rows |
| 01 | [01_sample_users.md](01_sample_users.md) | Seeded random sampling without replacement of legitimate and impostor users |
| 02 | [02_sample_sessions.md](02_sample_sessions.md) | Seeded shuffle of each user's sessions; first *k* = profile, rest = held out |
| 03 | [03_chunk_shapes.md](03_chunk_shapes.md) | Pause/click segmentation into strokes; translation + scale normalization; arc-length resampling |
| 04 | [04_match_shapes.md](04_match_shapes.md) | Banded (Sakoe–Chiba) Dynamic Time Warping with early abandoning; ratio rules for session and user |
| 05 | [05_sensitivity.md](05_sensitivity.md) | Sensitivity (formerly threshold) = matched impostor users / all impostor users |
| 06 | [06_plot_shapes.md](06_plot_shapes.md) | Plot every raw stroke (parallel workers) |
| 07 | [07_run_notebook.md](07_run_notebook.md) | Execute the session-progression notebook for a run |
| 08 | [08_plot_matches.md](08_plot_matches.md) | Find and draw the first matching user stroke for every matched impostor stroke |
| 09 | [09_genuine_check.md](09_genuine_check.md) | Score the user's own unused sessions against their own profile, next to the impostors |
| 10 | [10_plot_accuracy.md](10_plot_accuracy.md) | Sessions through (notebook counts) per legitimate and impostor user, one line per run of a hash folder |
| 12 | [12_pick_best.md](12_pick_best.md) | User accuracy (session accuracy breaks ties) per (split, sensitivity, sessions); keeps the best cell of each split in `runs/<hash>/best/` |
| 13 | [13_cohort_score.md](13_cohort_score.md) | Nearest-DTW scores against equal-size libraries; cohort score = share of other people a stroke is farther from; EER per split |
| 14 | [14_seed_check.md](14_seed_check.md) | Settings chosen on the training seed by 12 and 13, applied unchanged to new seeds; train vs test user accuracy |
| 15 | [15_plot_cohort.md](15_plot_cohort.md) | Per claim, each stroke next to its nearest stroke in every library (closer / farther); genuine vs impostor scores per split |
| 16 | [16_sweep_sensitivity.md](16_sweep_sensitivity.md) | Per fixed split, nearest-DTW cost once per (test, library) session pair; every library size a running minimum, every sensitivity a cut; TP/FP/FN/TN per setting |
| 17 | [17_plot_sweep.md](17_plot_sweep.md) | Balanced accuracy vs sensitivity and as a heatmap, FAR/FRR at 1, m/4, m/2, m sessions; no best setting picked |

## Words used on every page

- **Session**: one Balabit recording file. It belongs to the user whose folder it is in.
- **Chunk / stroke**: a piece of a session between two pauses or clicks (script 03). The two words mean the same thing.
- **Move / drag**: a stroke made with no button held (move) or with a button held (drag). They are only ever compared with strokes of the same kind.
- **Legitimate user / profile**: the user whose sessions form a shape library.
- **Impostor**: any other user whose sessions are tested against that profile.
- **Sensitivity**: in 05, 06 and the notebook, impostors matched / impostors (called *threshold* before 2026-10-14).

## Formulas shared by several scripts

Euclidean distance between two points, used for path length (03) and DTW (04):

$$d(p, q) = \sqrt{(x_p - x_q)^2 + (y_p - y_q)^2}$$

Path length of a stroke with points $p_1, \dots, p_m$:

$$L = \sum_{i=1}^{m-1} d(p_i, p_{i+1})$$

Session match ratio (04, 08, 09): the share of a session's strokes that have a matching stroke in the profile:

$$r = \frac{\text{strokes with a match}}{\text{all strokes of the session}}$$

## Results so far (short)

The numbers come from the runs described in the repository's `CLAUDE.md`. Each page gives its own numbers.

- Shape matching (01–05, 08, 09) does **not** tell users apart. Most matched strokes are near-straight lines, and almost every user draws those.
- The hull, One-Class SVM and DTW anomaly tests (old scripts 09–13) were removed on 2026-10-14 (DTW only from now on); they are in git history before that date.
