# How to run the EARL experiment

This folder tests whether mouse-movement shapes from legitimate users can be told apart from impostors, using the Balabit dataset. This guide covers setup, the three ways to run it, and where the results go. Every setting is explained in [CONFIG.md](CONFIG.md).

All commands below are run from the **repository root** (`thesis-mouse-biometrics/`). On Windows, replace `.venv/bin/python` with `.venv\Scripts\python`.

## The data

All of Balabit is used, raw (adviser, 2026-10-08): 10 users, 65 training sessions and 1,611 test sessions. **A session belongs to the user whose folder it is in**, for training and test files alike; no label file is used.

- Each user's sessions are their training sessions (5–7, about 2 hours each) followed by their test sessions (about 5 minutes each), each part shuffled per draw.
- So the first 5 session steps always use training sessions; test sessions come in from step 6–8 on, depending on the user.
- With `use_test_files: true` a user has 114–253 sessions, so `sessions_per_user` can go up to 114. With `use_test_files: false`, only training files are used and the limit is 5.
- Every script prints these counts and the limit when it starts.

## 1. One-time setup

The scripts need numba (fast shape matching) and nbconvert (running the notebook) on top of the usual packages.

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install nbformat nbconvert ipykernel "matplotlib-inline<0.2"
```

The `matplotlib-inline<0.2` pin matters only when the system matplotlib is older than 3.8 (Ubuntu's 3.6 is). Without it, notebook plots fail with `'RcParams' object has no attribute '_get'`.

The Balabit data is already in `experiment_earl/datasets/`; nothing to download.

## 2. Every run in three steps

1. **Edit [config.yaml](config.yaml)**: users, sessions, draws, data, matching settings.
2. **Run** the notebook, the sweep or the single trial (section 3).
3. **Open the results** in `experiment_earl/runs/<run name>/` (section 4). The script prints the folder.

Each distinct config gets its own run folder, so changing a setting never overwrites an older result. Running again with the same config reuses its folder.

## 3. What to run

### A. Notebook: sessions 1 → N (start here)

Tests `n_legitimate` legitimate users against `n_impostor` impostor users, with 1, 2, ... up to `sessions_per_user` sessions per user, repeated over `n_trials` random draws. Within a draw, each step keeps the sessions of the step before and adds one. It makes a bar graph (impostors matched per session step) and a heatmap (sessions × legitimate users).

```bash
.venv/bin/python experiment_earl/src/08_run_notebook.py
```

This executes `notebooks/session_progression.ipynb` and saves the executed copy, with all tables and plots, in the run folder. You can also open the notebook in VS Code or Jupyter, pick the `.venv` kernel and run all cells; its CSVs and figures go to the same run folder, but the executed copy stays in `notebooks/` (clear its outputs before committing).

### B. Sweep: every combination

Tries 1 up to `sweep_sessions_max` sessions per user, and every mix of legitimate and impostor users that fits in Balabit's 10 users (45 user mixes per session count, 225 cells at the default of 5), each averaged over `n_trials` draws. It reports where the results stop changing (saturate) and where they jump most.

```bash
.venv/bin/python experiment_earl/src/06_sweep.py
.venv/bin/python experiment_earl/src/06_sweep.py --trials 1    # quick look: one draw
```

It ignores `n_legitimate`, `n_impostor` and `sessions_per_user` (it tries them all). If it stops halfway, run it again: it continues from the last finished draw. Raising `sweep_sessions_max` above 5 brings test sessions in, but every extra session step compares all 10 users with each other again, so the run time grows quickly.

### C. Single trial, step by step (file-based)

One draw of `n_legitimate` + `n_impostor` users with `sessions_per_user` sessions each, with every intermediate file saved. Run the steps in order; each uses the files of the one before.

```bash
.venv/bin/python experiment_earl/src/01_sample_users.py      # pick users        -> temp/manifest.json
.venv/bin/python experiment_earl/src/02_sample_sessions.py   # pick sessions     -> temp/<class>/<user>/
.venv/bin/python experiment_earl/src/03_chunk_shapes.py      # cut into chunks   -> shapes/<class>/<user>/*.npz
.venv/bin/python experiment_earl/src/04_match_shapes.py      # compare chunks    -> results/trial_0.json
.venv/bin/python experiment_earl/src/05_threshold.py         # threshold         -> results/summary.csv
.venv/bin/python experiment_earl/src/07_plot_shapes.py       # optional: one PNG per chunk -> shapes/.../<session>/
```

Step 04 also scores each legitimate user's own **held-out** sessions (the ones not drawn) against their profile, as a sanity check: they should match better than the impostors do. With test files that is up to about 250 sessions per user.

`07_plot_shapes.py` draws whatever step 03 saved. It writes one image per chunk (tens of thousands for 5 sessions × 10 users), so `--user user21` and `--limit 50` keep it small.

### Working with an older run

Every script takes `--run <run folder name>`. It then uses that folder and the settings saved in it, whatever `config.yaml` says now:

```bash
.venv/bin/python experiment_earl/src/07_plot_shapes.py --run baseline_2707e0 --user user12
.venv/bin/python experiment_earl/src/08_run_notebook.py --run baseline_91da91
```

Run folder names are `<run_name>_<hash>`: `run_name` comes from the top of `config.yaml` and the hash from all other settings. Use a new `run_name` (for example `tol003`) to make runs easy to tell apart. Runs made before 2026-10-08 used training files only.

## 4. Where the results are

```
experiment_earl/runs/<run name>/
├── config.yaml          the exact settings this run used
├── run.json             when the folder was created and the git commit
├── notebooks/           executed notebook with all tables and plots                (A)
├── figures/
│   ├── session_progression.png          bar graph: impostors matched per session step   (A)
│   ├── session_progression_heatmap.png  heatmap: sessions × legitimate users            (A)
│   ├── sweep_heatmaps.png               one heatmap per session count                   (B)
│   └── sweep_lines.png                  threshold vs sessions / legitimate / impostors  (B)
├── results/
│   ├── session_progression.csv          one row per session step                        (A)
│   ├── session_progression_trials.csv   every draw, every impostor                      (A)
│   ├── session_progression_heatmap.csv  the heatmap's numbers                           (A)
│   ├── sweep/summary.csv                every combination: matched and threshold         (B)
│   ├── sweep/saturation.csv             where each curve flattens and jumps             (B)
│   ├── trial_0.json                     per-impostor and held-out match ratios          (C)
│   └── summary.csv                      threshold of the single trial                   (C)
├── shapes/              chunks (.npz) and chunk PNGs                                (C)
└── temp/                drawn sessions and manifest.json                           (C)
```

How to read them:

- **Impostors matched**: how many impostor users looked like a legitimate user. Lower is better.
- **Threshold** = impostors matched / impostor users, from 0 to 1. 0 is best: no impostor passed.
- **±** (std): how much the result changes from draw to draw. It is blank (NaN) when `n_trials` is 1, because one draw has no spread.

The whole `runs/` folder is git-ignored: results stay on your computer. Copy a run folder to share it.

## 5. How long it takes

For the scripts (01–07), the first run of a new chunking or matching setting is the slowest, because every shape comparison (DTW) is computed once and then cached in `experiment_earl/cache/` for all later runs. The notebook keeps its own cache only while it runs, so every notebook run takes about the same time.

| What | Typical time |
|---|---|
| Notebook, 3 + 2 users, 1–3 sessions, 20 draws | about 4–5 minutes |
| Notebook, 3 + 2 users, 1–5 sessions, 20 draws | about 10 minutes |
| Notebook, same, 1 draw | under a minute |
| Sweep, 1–5 sessions, 20 draws, first time | about 30 minutes; reruns that only redraw the figures take seconds |
| Single trial 01–05 | a few minutes (step 04 also scores the held-out sessions) |
| Chunk PNGs for 10 users × 5 sessions | about 25 minutes (about 44,000 images) |

More sessions per user means more shapes to compare, so runs beyond 5 sessions take noticeably longer.

## 6. Common problems

| Message | Fix |
|---|---|
| `... users do not fit in the 10 Balabit users` | Lower `n_legitimate` or `n_impostor`: they must add up to 10 or less. |
| `sessions_per_user = N but some user has only M sessions` | Lower `sessions_per_user` to M or less (114 with `use_test_files`, 5 without). |
| `sweep_sessions_max = N but some user has only M sessions` | Same for the sweep's `sweep_sessions_max`. |
| `KeyError` in the notebook or sweep right after the draws | `n_trials` is 0; set it to at least 1. |
| `No run '...' under .../runs` | The `--run` name is wrong; the message lists the existing runs. |
| `ModuleNotFoundError: numba` (or `nbformat`) | Use `.venv/bin/python`, or redo the setup in section 1. |
| `'RcParams' object has no attribute '_get'` | Run `.venv/bin/pip install "matplotlib-inline<0.2"`. |
| `No session .npz files under ...` from `07_plot_shapes.py` | Run steps 01–03 first for this config. |
