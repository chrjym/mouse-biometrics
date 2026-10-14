# Script documentation (`experiment_earl/src/`)

One page per script: what it does, the algorithm step by step, the formulas it uses, and why we chose that
algorithm or formula. Setting names in `code` are keys of [`config.yaml`](../config.yaml) (all explained in
[`CONFIG.md`](../CONFIG.md)); how to run each script is in [`README.md`](../README.md).
Each page ends with its own **References** (IEEE style, with DOI or link); all of them are collected in
[REFERENCES.md](REFERENCES.md).

## The pipeline at a glance

```
                          00_config  (settings, run folders, session loader, used by every script)
                              │
   ┌──────────────────────────┼─────────────────────────────────────────────────────────────┐
   │ A. Shape matching (does an impostor's stroke look like one of the user's strokes?)       │
   │   01 draw users → 02 draw sessions → 03 cut into strokes → 04 DTW match → 05 sensitivity │
   │   06 sweep every (sessions × legitimate × impostor) cell                                 │
   │   07 draw the strokes   08 run the notebook   14 draw matched pairs   15 genuine check   │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────────────────────────┐
   │ B. Adviser pipeline (2026-10-14): experiments [L, I] set by hand in config.yaml          │
   │   09 user × user × sensitivity   →   10 user × session × sensitivity → heatmap           │
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
| 06 | [06_sweep.md](06_sweep.md) | Full factorial sweep with nested draws; saturation (flat-from) and biggest-jump detection |
| 07 | [07_plot_shapes.md](07_plot_shapes.md) | Plot every raw stroke (parallel workers) |
| 08 | [08_run_notebook.md](08_run_notebook.md) | Execute the session-progression notebook for a run |
| 09 | [09_find_sensitivity.md](09_find_sensitivity.md) | Hand-set [legitimate, impostor] experiments × DTW tolerance grid; accuracy per side; best mean accuracy per experiment |
| 10 | [10_find_session.md](10_find_session.md) | Each E_k at its chosen sensitivity × 2 … 10 profile sessions; sensitivity heatmap |
| 14 | [14_plot_matches.md](14_plot_matches.md) | Find and draw the first matching user stroke for every matched impostor stroke |
| 15 | [15_genuine_check.md](15_genuine_check.md) | Score the user's own unused sessions against their own profile, next to the impostors |

## Words used on every page

- **Session**: one Balabit recording file. It belongs to the user whose folder it is in.
- **Chunk / stroke**: a piece of a session between two pauses or clicks (script 03). The two words mean the same thing.
- **Move / drag**: a stroke made with no button held (move) or with a button held (drag). They are only ever compared with strokes of the same kind.
- **Legitimate user / profile**: the user whose sessions form a shape library.
- **Impostor**: any other user whose sessions are tested against that profile.
- **Sensitivity**: in 05, 06 and the notebook, impostors matched / impostors (called *threshold* before 2026-10-14). In 09 and 10 it also names the DTW tolerance being tried, the config key `sensitivity` (formerly `dtw_tolerance`).
- **Accuracy** (09, 10): legitimate = own sessions accepted / legitimate users; impostor = impostors rejected / impostor users.

## Formulas shared by several scripts

Euclidean distance between two points, used for path length (03) and DTW (04):

$$d(p, q) = \sqrt{(x_p - x_q)^2 + (y_p - y_q)^2}$$

Path length of a stroke with points $p_1, \dots, p_m$:

$$L = \sum_{i=1}^{m-1} d(p_i, p_{i+1})$$

Session match ratio (04, 06, 09, 10, 14, 15): the share of a session's strokes that have a matching stroke in the profile:

$$r = \frac{\text{strokes with a match}}{\text{all strokes of the session}}$$

## Results so far (short)

The numbers come from the runs described in the repository's `CLAUDE.md`. Each page gives its own numbers.

- Shape matching (01–06, 14, 15) does **not** tell users apart. Most matched strokes are near-straight lines, and almost every user draws those.
- Find the sensitivity / sessions (09, 10): at the adviser's grid (`sensitivity` 0.2–1.0) every legitimate user is accepted and every impostor goes through, for every E_k and 2–10 sessions.
- The hull, One-Class SVM and DTW anomaly tests (old scripts 09–13) were removed on 2026-10-14 (DTW only from now on); they are in git history before that date.
