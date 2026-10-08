# config.yaml: what each setting does

`experiment_earl/config.yaml` is the single settings file for every script in `experiment_earl/src/`. To change how an experiment behaves, edit the value here instead of the code. Each script loads it through `00_config.py`. For how to run the scripts and the notebook, see [README.md](README.md).

## The data

All of Balabit is used, raw (adviser, 2026-10-08): 65 training sessions and 1,611 test sessions for 10 users. A session belongs to the user whose folder it is in; no label file is used. Every script prints the counts and the session limit when it starts.

## Every config gets its own folder

Nothing is overwritten when you change a setting. The scripts store everything for a config under `experiment_earl/runs/<name>_<hash>/`:

```
runs/baseline_2707e0/
├── config.yaml     snapshot of the settings used (with comments)
├── run.json        when the folder was created and the git commit
├── results/        trial_0.json, summary.csv, session_progression*.csv, sweep/
├── figures/        sweep_heatmaps.png, sweep_lines.png, session_progression*.png
├── notebooks/      executed copy of session_progression.ipynb (08_run_notebook.py)
├── shapes/         chunks as .npz and, after 07, the PNGs   (regenerable)
└── temp/           manifest.json and the copied sessions    (regenerable)
```

- **Name:** `run_name` (the label at the top of `config.yaml`) plus a 6-character hash of all the other settings. If `run_name` is empty, the label is built from the tolerance, pause gap and `resample_n`.
- **Same settings, same folder:** running again with an unchanged config reuses its folder, so the sweep resumes. **Any change gives a new folder**, and the old one stays as it was.
- **Pick an old run:** every script takes `--run <folder name>`, for example `07_plot_shapes.py --run baseline_2707e0`. The notebook helper takes it too; the notebook itself reads the `EARL_RUN` environment variable.
- **Shared cache:** `experiment_earl/cache/pairs.pkl` holds DTW results for all runs. Its keys contain the chunking, band and tolerance settings, so a new run reuses whatever is still valid.
- **Git:** the whole `runs/` folder and `cache/` are git-ignored. Runs stay on your disk for reference but are not committed, so copy a run folder somewhere safe if you need to share it.

## How the pipeline uses it

```
01_sample_users      draws legitimate + impostor users
02_sample_sessions   draws sessions per user, copies them to temp/
03_chunk_shapes      cuts each session into chunks (shapes)
04_match_shapes      compares impostor chunks with the legitimate library (DTW)
05_threshold         threshold = impostors matched / total impostors
06_sweep             repeats the whole thing over many user/session counts
07_plot_shapes       draws every chunk as a PNG
08_run_notebook      executes the notebook and saves the copy in the run folder
09_build_hulls       per user: raw data -> chunk end points at (0, 0) -> convex hull -> concave hull
10_hull_anomaly      windows of strokes outside a user's concave hull: own sessions (FRR) vs other users (FAR)
11_ocsvm_anomaly     the same test with a per-user One-Class SVM on several features per stroke
```

Scripts 01–05 run **one trial** with `n_legitimate`, `n_impostor` and `sessions_per_user`. The **notebook** uses the same three settings plus `n_trials`: it tests 1, 2, ... up to `sessions_per_user` sessions per user, repeated over `n_trials` draws. Script 06 runs the **full sweep** and ignores `n_legitimate`, `n_impostor` and `sessions_per_user`; it tries every combination itself.

## Data and sampling

| Setting | Default | Used by | Meaning |
|---|---|---|---|
| `run_name` | `baseline` | all | Label for this config's folder under `runs/`. It is not part of the hash, so renaming it does not change which settings the folder stands for. |
| `seed` | 42 | 01, 02, 06 | Starting number for every random choice (which users, which sessions). The same seed gives the same draw, so a result can be repeated. The sweep uses `seed`, `seed + 1`, ... for its draws. |
| `dataset_dir` | `datasets/balabit/training_files` | all | Balabit training sessions, relative to `experiment_earl/`. A session belongs to the user whose folder it is in. |
| `test_dir` | `datasets/balabit/test_files` | all | Balabit test sessions, relative to `experiment_earl/`. Also counted by folder: every session in `test_files/user12/` is user12. |
| `use_test_files` | true | all | Adds each user's `test_files` sessions after their training sessions (up to 114 per user instead of 5). |
| `n_legitimate` | 3 | 01, notebook | How many users are "legitimate" in a single trial or notebook run. Their shapes form the library that impostors are compared against. The notebook heatmap also shows the first 1, 2, ... up to this many of them. |
| `n_impostor` | 2 | 01, notebook | How many other users act as impostors in a single trial. Balabit has only 10 users, so `n_legitimate + n_impostor` must be 10 or less. |
| `sessions_per_user` | 5 | 02, notebook | Sessions drawn per user in a single trial. In the notebook it is the maximum: it tests 1, 2, ... up to this value, and the sessions of each step include those of the step before. A user's sessions are ordered training first, then test, so steps up to 5 use training sessions only. At most 114 with `use_test_files` (user20 has 7 + 107), 5 without; every script prints the limit. |

## Chunking (script 03)

A session is a long stream of mouse points. A *chunk* is one continuous stroke of movement.

| Setting | Default | Meaning |
|---|---|---|
| `pause_gap_s` | 0.5 | A pause longer than this many seconds starts a new chunk. Every click (`Pressed` or `Released`) also starts one. |
| `min_points` | 10 | Chunks with fewer recorded points are dropped as jitter. |
| `min_length_px` | 0 | Chunks whose path is shorter than this many pixels are dropped. 0 turns the filter off. |
| `resample_n` | 64 | Each chunk is redrawn with this many evenly spaced points, so shapes of different lengths and speeds can be compared. Each chunk is first moved to start at the origin and scaled so its bounding-box diagonal is 1. |

Chunks that are not comparable (zero length) still count in the denominator of a session's match ratio, so every recorded stroke is included.

## Matching (script 04)

| Setting | Default | Meaning |
|---|---|---|
| `dtw_band` | 0.1 | The comparison (banded DTW) may only stretch one shape against the other within this share of `resample_n`. It keeps matching fast and stops absurd alignments. |
| `dtw_tolerance` | 0.02 | The key setting. Two chunks match when their mean DTW distance per point is at or below this value. Lower is stricter. At 0.15 about 99% of all chunks matched, so the metric told nothing; 0.02 keeps the results from being all 0 or all 1. |
| `match_shape_ratio` | 0.3 | A session matches a legitimate profile when at least this share of its chunks match a chunk of the same kind (move or drag) in that profile. (Assumption A2 in `EARL_EXECUTION_PLAN.md`.) |
| `match_session_ratio` | 0.5 | An impostor user counts as **matched** when at least this share of their sessions match any single legitimate profile. This decides `matched_detected`. (Assumption A1 in the plan.) |

The threshold is `matched impostor users / total impostor users`. 0 is best: impostors never look like the legitimate users.

## Sweep (script 06)

| Setting | Default | Meaning |
|---|---|---|
| `n_trials` | 20 | Random draws of users and sessions that every sweep cell (and every notebook step) is averaged over. It does not change what is tested, only how steady the averages are: more draws give steadier numbers but take longer. |
| `sweep_sessions_max` | 5 | The sweep tries 1 up to this many sessions per user. Every Balabit user has at least 5. |
| `sweep_delta` | 0.05 | A step (one more session or one more user) that changes the mean threshold by less than this counts as "flat" (saturated). Used for the `flat_from` column in `results/sweep/saturation.csv`. |

The sweep covers every combination of sessions (1 to `sweep_sessions_max`), legitimate users (1 to 9) and impostor users (1 to 10 minus legitimate users).

## Hulls (script 09)

| Setting | Default | Meaning |
|---|---|---|
| `concave_ratio` | 0.1 | Tightness of the concave hull around each user's chunk end points: 0 follows the points as closely as possible, 1 gives the convex hull. The hulls use `sessions_per_user` sessions per user and the chunking settings above. |

## Hull anomaly test (script 10)

| Setting | Default | Meaning |
|---|---|---|
| `anomaly_enroll_sessions` | 4 | Training sessions that build each user's concave hull. Must be lower than the user's training session count (5–7), so at least one is left to test. |
| `anomaly_window` | 30 | Strokes (chunks) per window. Each session is checked window by window, sliding one stroke at a time. |
| `anomaly_outside_share` | 0.2 | A window is an anomaly when more than this share of its strokes end outside the hull. Higher = fewer own sessions flagged, but more impostors missed. |

The hull also uses `concave_ratio` and the chunking settings.

## One-Class SVM anomaly test (script 11)

Uses `anomaly_enroll_sessions` and `anomaly_window` from the hull test, so both scripts test the same sessions.

| Setting | Default | Meaning |
|---|---|---|
| `ocsvm_features` | `[dx, dy, path_length, straightness, mean_speed, duration]` | Numbers per stroke the SVM learns from. `dx`, `dy`: net movement (the hull's end point). `path_length`: distance travelled (log). `straightness`: net movement / path length. `mean_speed`: path length / duration (log). `duration`: seconds. Remove a name to test without it. |
| `ocsvm_nu` | 0.05 | About this share of the user's own training strokes may fall outside the learned region. Larger = tighter region: more own sessions flagged, fewer impostors missed. |
| `ocsvm_gamma` | `scale` | How far one training stroke's influence reaches. `scale` is automatic; a number such as 0.1 (smooth) to 10 (tight, can overfit). |
| `ocsvm_max_train` | 4000 | Random training strokes per model; the SVM slows down quickly with more. 0 = all. |
| `ocsvm_resample_ms` | 0 | 0 = raw points. 125 = each stroke's path on a 125 ms grid before measuring length, straightness and speed, so users who log every ~16 ms and every ~110 ms compare fairly. |
| `ocsvm_flag_score` | 0.0 | A window is an anomaly when its mean SVM score is below this. 0 is the learned boundary; lower = fewer flags. |

## When you change a setting

Any change to a value (except `run_name`) makes the next script run create a new folder under `runs/`, so nothing needs deleting or resetting. Then:

- **Single trial:** run 01 → 05 again (or the sweep, or the notebook). The new folder starts empty.
- **Speed:** DTW results are shared through `cache/pairs.pkl`. Changing only `match_session_ratio`, `sweep_delta`, `sweep_sessions_max`, `n_trials` or `seed` reuses all of them; changing chunking, band or tolerance recomputes what it must.
- **Going back:** run the scripts with `--run <old folder>` to read or extend an older run with its own saved settings, whatever `config.yaml` says now.

## Limits to remember

- Balabit has only 10 users, so the total of legitimate and impostor users can never go above 10.
- The notebook `notebooks/session_progression.ipynb` reads this file and sets nothing itself. It stops with a message if the user counts or `sessions_per_user` do not fit Balabit. Its outputs go to the current run folder.
- The tolerance of 0.02 is a baseline, not a validated value: in earlier tuning, a user's own held-out sessions never matched more than impostors did.
