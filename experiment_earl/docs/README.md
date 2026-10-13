# Script documentation (`experiment_earl/src/`)

One page per script: what it does, the algorithm step by step, the formulas it uses, and why we chose that
algorithm or formula. Setting names in `code` are keys of [`config.yaml`](../config.yaml) (all explained in
[`CONFIG.md`](../CONFIG.md)); how to run each script is in [`README.md`](../README.md).

## The pipeline at a glance

```
                          00_config  (settings, run folders, session loader, used by every script)
                              │
   ┌──────────────────────────┼─────────────────────────────────────────────────────────────┐
   │ A. Shape matching (does an impostor's stroke look like one of the user's strokes?)       │
   │   01 draw users → 02 draw sessions → 03 cut into strokes → 04 DTW matching → 05 threshold│
   │   06 sweep every (sessions × legitimate × impostor) cell                                 │
   │   07 draw the strokes   08 run the notebook   14 draw matched pairs   15 genuine check   │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────────────────────────┐
   │ B. Anomaly tests (is this window of strokes unlike the user's own?)                       │
   │   09 hulls per user (picture)                                                            │
   │   10 concave hull test   11 One-Class SVM test   12 DTW library test                     │
   │   13 rerun 10–12 with 1 … k registered sessions                                          │
   └──────────────────────────────────────────────────────────────────────────────────────────┘
```

| Script | Page | Algorithm in one line |
|---|---|---|
| 00 | [00_config.md](00_config.md) | Config loading, SHA-1 run folders, seeded session order, cleaning raw Balabit rows |
| 01 | [01_sample_users.md](01_sample_users.md) | Seeded random sampling without replacement of legitimate and impostor users |
| 02 | [02_sample_sessions.md](02_sample_sessions.md) | Seeded shuffle of each user's sessions; first *k* = profile, rest = held out |
| 03 | [03_chunk_shapes.md](03_chunk_shapes.md) | Pause/click segmentation into strokes; translation + scale normalization; arc-length resampling |
| 04 | [04_match_shapes.md](04_match_shapes.md) | Banded (Sakoe–Chiba) Dynamic Time Warping with early abandoning; ratio rules for session and user |
| 05 | [05_threshold.md](05_threshold.md) | Threshold = matched impostor users / all impostor users |
| 06 | [06_sweep.md](06_sweep.md) | Full factorial sweep with nested draws; saturation (flat-from) and biggest-jump detection |
| 07 | [07_plot_shapes.md](07_plot_shapes.md) | Plot every raw stroke (parallel workers) |
| 08 | [08_run_notebook.md](08_run_notebook.md) | Execute the session-progression notebook for a run |
| 09 | [09_build_hulls.md](09_build_hulls.md) | Stroke displacement vectors → convex hull → concave hull (Delaunay erosion) |
| 10 | [10_hull_anomaly.md](10_hull_anomaly.md) | Point-in-polygon test, sliding window, leave-one-out FRR, FAR, Equal Error Rate |
| 11 | [11_ocsvm_anomaly.md](11_ocsvm_anomaly.md) | Six stroke features → RobustScaler → One-Class SVM (RBF kernel) |
| 12 | [12_dtw_anomaly.md](12_dtw_anomaly.md) | Same window test, but "outside" = no DTW match in the user's shape library |
| 13 | [13_enroll_sweep.md](13_enroll_sweep.md) | Rerun 10–12 for 1 … `anomaly_enroll_sessions` registered sessions |
| 14 | [14_plot_matches.md](14_plot_matches.md) | Find and draw the first matching user stroke for every matched impostor stroke |
| 15 | [15_genuine_check.md](15_genuine_check.md) | Score the user's own unused sessions against their own profile, next to the impostors |

## Words used on every page

- **Session**: one Balabit recording file. It belongs to the user whose folder it is in.
- **Chunk / stroke**: a piece of a session between two pauses or clicks (script 03). The two words mean the same thing.
- **Move / drag**: a stroke made with no button held (move) or with a button held (drag). They are only ever compared with strokes of the same kind.
- **Legitimate user / profile**: the user whose sessions form a library, hull or model.
- **Impostor**: any other user whose sessions are tested against that profile.
- **FRR** (False Rejection Rate): share of the user's own sessions that the test rejects.
- **FAR** (False Acceptance Rate): share of impostor sessions that the test accepts.
- **EER** (Equal Error Rate): the error where FRR = FAR when the decision cut is moved. 0 is perfect, 0.5 is guessing.

## Formulas shared by several scripts

Euclidean distance between two points, used for path length (03), DTW (04), and stroke distance (09, 11):

$$d(p, q) = \sqrt{(x_p - x_q)^2 + (y_p - y_q)^2}$$

Path length of a stroke with points $p_1, \dots, p_m$:

$$L = \sum_{i=1}^{m-1} d(p_i, p_{i+1})$$

Net movement (displacement) of a stroke, used by the hulls (09, 10) and the SVM (11):

$$(\Delta x, \Delta y) = p_m - p_1$$

Session match ratio (04, 06, 14, 15): the share of a session's strokes that have a matching stroke in the profile:

$$r = \frac{\text{strokes with a match}}{\text{all strokes of the session}}$$

Sliding-window share (10, 12): with $o_i = 1$ when stroke $i$ is anomalous and window size $W$,

$$w_j = \frac{1}{W} \sum_{i=j}^{j+W-1} o_i$$

## Results so far (short)

The numbers come from the runs described in the repository's `CLAUDE.md`. Each page gives its own numbers.

- Shape matching (01–06, 14, 15) does **not** tell users apart. Most matched strokes are near-straight lines, and almost every user draws those.
- Among the anomaly tests (10–13), the One-Class SVM does best (EER ≈ 30%). The hull and DTW tests are both at ≈ 44%. Registering more sessions moves FRR against FAR but does not lower the EER.
