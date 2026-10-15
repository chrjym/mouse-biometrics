# config.yaml: what each setting does

`experiment_earl/config.yaml` is the single settings file for every script in `experiment_earl/src/`. To change how an experiment behaves, edit the value here instead of the code. Each script loads it through `00_config.py`. For how to run the scripts and the notebook, see [README.md](README.md).

## The data

All of Balabit is used, raw (adviser, 2026-10-08): 1,676 sessions for 10 users. The former `training_files` and `test_files` are merged into one folder per user, `datasets/balabit/users/<user>/` (adviser, 2026-10-14). A session belongs to the user whose folder it is in; no label file is used. Every script prints the counts and the session limit when it starts.

## Every config gets its own folder

Nothing is overwritten when you change a setting. The scripts store everything for a config under `experiment_earl/runs/<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>/`:

```
runs/1a2b3c/1_9_0.04_10/
├── config.yaml     snapshot of the settings used (with comments)
├── run.json        when the folder was created and the git commit
├── results/        trial_0.json, summary.csv, session_progression*.csv, sweep/
├── figures/        sweep_heatmaps.png, sweep_lines.png, session_progression*.png
├── notebooks/      executed copy of session_progression.ipynb (08_run_notebook.py)
├── shapes/         chunks as .npz and, after 07, the PNGs   (regenerable)
└── temp/           manifest.json and the copied sessions    (regenerable)
```

- **Name:** `<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>`, for example `1a2b3c/1_9_0.04_10`. The 6-character hash covers every other setting, so runs that differ only in those four sit side by side in one hash folder.
- **Same settings, same folder:** running again with an unchanged config reuses its folder, so the sweep resumes. **Any change gives a new folder**, and the old one stays as it was.
- **Pick an old run:** every script takes `--run <folder name>`, for example `07_plot_shapes.py --run 1a2b3c/1_9_0.04_10`. The notebook helper takes it too; the notebook itself reads the `EARL_RUN` environment variable.
- **Shared cache:** `experiment_earl/cache/pairs.pkl` holds DTW results for all runs. Its keys contain the chunking, band and tolerance settings, so a new run reuses whatever is still valid.
- **Git:** the whole `runs/` folder and `cache/` are git-ignored. Runs stay on your disk for reference but are not committed, so copy a run folder somewhere safe if you need to share it.

## How the pipeline uses it

```
01_sample_users      draws legitimate + impostor users
02_sample_sessions   draws sessions per user, copies them to temp/
03_chunk_shapes      cuts each session into chunks (shapes)
04_match_shapes      compares impostor chunks with the legitimate library (DTW)
05_sensitivity       sensitivity = impostors matched / total impostors (formerly "threshold")
06_sweep             repeats the whole thing over many user/session counts
07_plot_shapes       draws every chunk as a PNG
08_run_notebook      executes the notebook and saves the copy in the run folder
09_find_sensitivity  the drawn legitimate users and impostors at the configured sensitivity, user by user
10_find_session      the same at 1, 2, ... sessions_per_user profile sessions; sensitivity heatmap
14_plot_matches      draws the impostor strokes that matched each legitimate user in the notebook
15_genuine_check     the legitimate users' own unused sessions against their own profile, next to the impostors
16_plot_accuracy     every run of one runs/<hash>/ folder: share of strokes matched per legitimate and impostor user
```

**One draw, fixed for the whole run** (user decision, 2026-10-12): scripts 01–05, the **notebook**, 09, 10, 14 and 15 make one RNG draw from `seed` that picks the `n_legitimate` legitimate users, the `n_impostor` impostors and each user's session order. Nothing is redrawn afterwards, so every step, figure and table of a run uses the same users and sessions. The notebook tests 1, 2, ... up to `sessions_per_user` sessions per user on that draw. Scripts 09 and 10 use the same draw and settings (the main configuration). Script 06 runs the **full sweep** and is the only one that uses `n_trials`: it ignores `n_legitimate`, `n_impostor` and `sessions_per_user` and tries every combination itself over `n_trials` draws.

## Data and sampling

| Setting | Default | Used by | Meaning |
|---|---|---|---|
| `seed` | 934 | 01, 02, 06, 09, 10, 14, 15, notebook | Picks the users and sessions once (which users are legitimate, which are impostors, the order of each user's sessions). The same seed gives the same users and sessions, so a result can be repeated. Only the sweep makes more draws, with `seed`, `seed + 1`, ... |
| `dataset_dir` | `datasets/balabit/users` | all | Balabit sessions, one folder per user (training and test files merged, adviser 2026-10-14), relative to `experiment_earl/`. A session belongs to the user whose folder it is in. |
| `n_legitimate` | 3 | 01, notebook, 09, 10, 14, 15 | How many users are "legitimate" in a single trial or notebook run. Their shapes form the library that impostors are compared against. The notebook heatmap also shows the first 1, 2, ... up to this many of them. |
| `n_impostor` | 2 | 01, notebook, 09, 10, 14, 15 | How many other users act as impostors in a single trial. Balabit has only 10 users, so `n_legitimate + n_impostor` must be 10 or less. |
| `sessions_per_user` | 5 | 02, notebook, 09, 10, 14, 15 | Sessions drawn per user in a single trial and 09's profile size. In the notebook and 10 it is the maximum: it tests 1, 2, ... up to this value, and the sessions of each step include those of the step before. At most 114 (user20); every script prints the limit. |

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
| `sensitivity` | 0.02 | Formerly `dtw_tolerance` (renamed 2026-10-14; old run snapshots are read with the old name too). The key setting. Two chunks match when their mean DTW distance per point is at or below this value. Lower is stricter. At 0.15 about 99% of all chunks matched, so the metric told nothing; 0.02 keeps the results from being all 0 or all 1. |
| `match_shape_ratio` | 0.2 | A session matches a legitimate profile when at least this share of its chunks match a chunk of the same kind (move or drag) in that profile. (Assumption A2 in `EARL_EXECUTION_PLAN.md`.) |
| `match_session_ratio` | 0.5 | An impostor user counts as **matched** when at least this share of their sessions match any single legitimate profile. This decides `matched_detected`. (Assumption A1 in the plan.) |

The **sensitivity** (called *threshold* before 2026-10-14) is `matched impostor users / total impostor users`. 0 is best: impostors never look like the legitimate users.

## Sweep (script 06)

| Setting | Default | Meaning |
|---|---|---|
| `n_trials` | 20 | Sweep only: random draws of users and sessions that every sweep cell is averaged over. It does not change what is tested, only how steady the averages are: more draws give steadier numbers but take longer. The notebook, 09, 10, 14 and 15 ignore it: they use one fixed draw from `seed`. |
| `sweep_sessions_max` | 5 | The sweep tries 1 up to this many sessions per user. Every Balabit user has at least 5. |
| `sweep_delta` | 0.05 | A step (one more session or one more user) that changes the mean sensitivity by less than this counts as "flat" (saturated). Used for the `flat_from` column in `results/sweep/saturation.csv`. |

The sweep covers every combination of sessions (1 to `sweep_sessions_max`), legitimate users (1 to 9) and impostor users (1 to 10 minus legitimate users).

## Find the sensitivity (09) and the sessions (10)

No settings of their own (user decision 2026-10-14): they use `seed`, `n_legitimate`, `n_impostor`, `sessions_per_user` and `sensitivity` from above, plus the matching ratios. Each user's 2 sessions after `sessions_per_user` are the tested sessions. To compare sensitivities, change `sensitivity` and rerun; every value gets its own run folder.

## When you change a setting

Any change to a value makes the next script run create a new folder under `runs/`, so nothing needs deleting or resetting. Then:

- **Single trial:** run 01 → 05 again (or the sweep, or the notebook). The new folder starts empty.
- **Speed:** DTW results are shared through `cache/pairs.pkl`. Changing only `match_session_ratio`, `sweep_delta`, `sweep_sessions_max`, `n_trials` or `seed` reuses all of them; changing chunking, `dtw_band` or `sensitivity` recomputes what it must.
- **Going back:** run the scripts with `--run <old folder>` to read or extend an older run with its own saved settings, whatever `config.yaml` says now.

## Limits to remember

- Balabit has only 10 users, so the total of legitimate and impostor users can never go above 10.
- The notebook `notebooks/session_progression.ipynb` reads this file and sets nothing itself. It stops with a message if the user counts or `sessions_per_user` do not fit Balabit. Its outputs go to the current run folder.
- The tolerance of 0.02 is a baseline, not a validated value: in earlier tuning, a user's own held-out sessions never matched more than impostors did.
