# config.yaml: what each setting does

`experiment_earl/config.yaml` is the single settings file for every script in `experiment_earl/src/`. To change how an experiment behaves, edit the value here instead of the code. Each script loads it through `00_config.py`.

## Every config gets its own folder

Nothing is overwritten when you change a setting. The scripts store everything for a config under `experiment_earl/runs/<name>_<hash>/`:

```
runs/baseline_2707e0/
├── config.yaml     snapshot of the settings used (with comments)
├── run.json        when the folder was created and the git commit
├── results/        trial_0.json, summary.csv, session_progression*.csv, sweep/
├── figures/        sweep_heatmaps.png, sweep_lines.png, session_progression*.png
├── notebooks/      executed copy of session_progression.ipynb (08_run_notebook.py)
├── shapes/         chunks as .npz and, after 07, the PNGs   (git-ignored, regenerable)
└── temp/           manifest.json and the copied sessions    (git-ignored, regenerable)
```

- **Name:** `run_name` (the label at the top of `config.yaml`) plus a 6-character hash of all the other settings. If `run_name` is empty, the label is built from the tolerance, pause gap and `resample_n`.
- **Same settings, same folder:** running again with an unchanged config reuses its folder, so the sweep resumes. **Any change gives a new folder**, and the old one stays as it was.
- **Pick an old run:** every script takes `--run <folder name>`, for example `07_plot_shapes.py --run baseline_2707e0`. The notebook helper takes it too; the notebook itself reads the `EARL_RUN` environment variable.
- **Shared cache:** `experiment_earl/cache/pairs.pkl` holds DTW results for all runs. Its keys contain the chunking, band and tolerance settings, so a new run reuses whatever is still valid.
- **Git:** results, figures, the snapshot and the executed notebook are committed; `shapes/`, `temp/` and `cache/` are ignored because they are large and can be regenerated.

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
```

Scripts 01–05 run **one trial**. Script 06 runs the **full sweep** and ignores the three "one trial" settings below (`n_legitimate`, `n_impostor`, `sessions_per_user`).

## Data and sampling

| Setting | Default | Used by | Meaning |
|---|---|---|---|
| `run_name` | `baseline` | all | Label for this config's folder under `runs/`. It is not part of the hash, so renaming it does not change which settings the folder stands for. |
| `seed` | 42 | 01, 02, 06 | Starting number for every random choice (which users, which sessions). The same seed gives the same draw, so a result can be repeated. The sweep uses `seed`, `seed + 1`, ... for its draws. |
| `dataset_dir` | `datasets/balabit/training_files` | all | Folder with the raw Balabit sessions, relative to `experiment_earl/`. Only the training files are used. |
| `n_legitimate` | 3 | 01 | How many users are "legitimate" in a single trial. Their shapes form the library that impostors are compared against. |
| `n_impostor` | 7 | 01 | How many other users act as impostors in a single trial. Balabit has only 10 users, so `n_legitimate + n_impostor` must be 10 or less. |
| `sessions_per_user` | 5 | 02 | Sessions drawn per user in a single trial. If a user has fewer, all of theirs are used (Balabit users have 5–7 training sessions). |

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
| `n_trials` | 20 | Random draws of users and sessions that every sweep cell is averaged over. More draws give steadier numbers but take longer. |
| `sweep_sessions_max` | 5 | The sweep tries 1 up to this many sessions per user. Every Balabit user has at least 5. |
| `sweep_delta` | 0.05 | A step (one more session or one more user) that changes the mean threshold by less than this counts as "flat" (saturated). Used for the `flat_from` column in `results/sweep/saturation.csv`. |

The sweep covers every combination of sessions (1 to `sweep_sessions_max`), legitimate users (1 to 9) and impostor users (1 to 10 minus legitimate users).

## When you change a setting

Any change to a value (except `run_name`) makes the next script run create a new folder under `runs/`, so nothing needs deleting or resetting. Then:

- **Single trial:** run 01 → 05 again (or the sweep, or the notebook). The new folder starts empty.
- **Speed:** DTW results are shared through `cache/pairs.pkl`. Changing only `match_session_ratio`, `sweep_delta`, `sweep_sessions_max`, `n_trials` or `seed` reuses all of them; changing chunking, band or tolerance recomputes what it must.
- **Going back:** run the scripts with `--run <old folder>` to read or extend an older run with its own saved settings, whatever `config.yaml` says now.

## Limits to remember

- Balabit has only 10 users, so the total of legitimate and impostor users can never go above 10.
- The notebook `notebooks/session_progression.ipynb` reads this file too, but sets its own user and session counts (3 legitimate, 2 impostor, 1–3 sessions). Its outputs go to the current run folder.
- The tolerance of 0.02 is a baseline, not a validated value: in earlier tuning, a user's own held-out sessions never matched more than impostors did.
