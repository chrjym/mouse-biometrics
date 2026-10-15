# How to run the EARL experiment

This folder tests whether mouse-movement shapes from legitimate users can be told apart from impostors, using the Balabit dataset. This guide covers setup, the ways to run it, exporting the shapes as images, the find-the-sensitivity and find-the-sessions experiments, and where the results go. Every setting is explained in [CONFIG.md](CONFIG.md); how each script works (algorithm, formulas, and why) is in [docs/](docs/README.md).

All commands below are run from the **repository root** (`thesis-mouse-biometrics/`). On Windows, replace `.venv/bin/python` with `.venv\Scripts\python`.

## The data

All of Balabit is used, raw (adviser, 2026-10-08): 10 users, 1,676 sessions. Balabit's `training_files` and `test_files` are merged into **one folder per user**, `datasets/balabit/users/<user>/` (adviser, 2026-10-14). **A session belongs to the user whose folder it is in**; no label file is used.

- Each user has 114–253 sessions: 5–7 former training sessions (about 2 hours each) and the rest former test sessions (about 5 minutes each). The folder no longer says which is which.
- Each user's sessions are shuffled once with `seed`; step k takes the first k, so step k+1 contains step k.
- Every script prints these counts and the session limit (114) when it starts.

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

1. **Edit [config.yaml](config.yaml)**: users, seed, sessions, data, matching settings.
2. **Run** the notebook, the sweep or the single trial (section 3).
3. **Open the results** in `experiment_earl/runs/<hash>/<L>_<I>_<sensitivity>_<sessions>/` (section 4). The script prints the folder.

Each distinct config gets its own run folder, so changing a setting never overwrites an older result. Running again with the same config reuses its folder.

## 3. What to run

### A. Notebook: sessions 1 → N (start here)

Tests `n_legitimate` legitimate users against `n_impostor` impostor users, with 1, 2, ... up to `sessions_per_user` sessions per user. **One RNG draw from `seed` fixes the legitimate users, the impostors and each user's session order for the whole run**; nothing is redrawn between steps or figures. Each step keeps the sessions of the step before and adds one. It makes a bar graph (impostors matched per session step), one bar graph per legitimate user, and a heatmap (sessions × legitimate users).

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

It ignores `n_legitimate`, `n_impostor` and `sessions_per_user` (it tries them all). If it stops halfway, run it again: it continues from the last finished draw. Raising `sweep_sessions_max` adds sessions, but every extra session step compares all 10 users with each other again, so the run time grows quickly.

### C. Single trial, step by step (file-based)

One draw of `n_legitimate` + `n_impostor` users with `sessions_per_user` sessions each, with every intermediate file saved. Run the steps in order; each uses the files of the one before.

```bash
.venv/bin/python experiment_earl/src/01_sample_users.py      # pick users        -> temp/manifest.json
.venv/bin/python experiment_earl/src/02_sample_sessions.py   # pick sessions     -> temp/<class>/<user>/
.venv/bin/python experiment_earl/src/03_chunk_shapes.py      # cut into chunks   -> shapes/<class>/<user>/*.npz
.venv/bin/python experiment_earl/src/04_match_shapes.py      # compare chunks    -> results/trial_0.json
.venv/bin/python experiment_earl/src/05_sensitivity.py       # sensitivity       -> results/summary.csv
```

Step 04 also scores each legitimate user's own **held-out** sessions (the ones not drawn) against their profile, as a sanity check: they should match better than the impostors do. That is up to about 250 sessions per user.

### D. Export the shapes (lines) as images

Every chunk that step 03 cut out is one shape: a continuous mouse line between two pauses or clicks. Step 03 saves them as data (`.npz`); `07_plot_shapes.py` draws each one as a PNG, in a folder per user and session.

It needs the shapes of step 03, so run steps 01–03 first (once per config), then export:

```bash
.venv/bin/python experiment_earl/src/01_sample_users.py
.venv/bin/python experiment_earl/src/02_sample_sessions.py
.venv/bin/python experiment_earl/src/03_chunk_shapes.py      # saves the shapes as .npz

.venv/bin/python experiment_earl/src/07_plot_shapes.py       # draws every shape as a PNG
```

Useful options:

```bash
.venv/bin/python experiment_earl/src/07_plot_shapes.py --user user21              # one user only
.venv/bin/python experiment_earl/src/07_plot_shapes.py --user user21 --user user9 # several users
.venv/bin/python experiment_earl/src/07_plot_shapes.py --limit 50                 # at most 50 shapes per session
.venv/bin/python experiment_earl/src/07_plot_shapes.py --no-overview              # skip the overview grid
.venv/bin/python experiment_earl/src/07_plot_shapes.py --run 1a2b3c/1_9_0.04_10   # shapes of an older run
```

What it writes, inside the run folder:

```
shapes/<legitimate|impostor>/<user>/
├── session_0041905381.npz          the shapes as data (from step 03)
└── session_0041905381/
    ├── chunk_0000_move.png         one image per shape
    ├── chunk_0001_drag.png
    ├── ...
    └── overview.png                grid of the session's first 100 shapes
```

Each image shows the real screen path: green dot = start, red dot = end, blue = mouse move, orange = drag (button held). The title gives the shape's number, length in pixels and duration. A session has hundreds to over a thousand shapes, so all users can mean tens of thousands of images (about 25 minutes for 10 users × 5 sessions); `--user` and `--limit` keep it small.

### E. Find the sensitivity (User × User × Sensitivity)

The adviser's pipeline (2026-10-14): raw → RNG (legitimate users, impostor users, sessions) → strokes (chunk shapes) → **user × user × sensitivity** → user × session × sensitivity → sensitivity → heatmap. Matching uses DTW only.

Everything comes from the main configuration (user decision 2026-10-14; the separate 09/10 settings were removed): the same draw as the notebook (`seed`, `n_legitimate` legitimate users, `n_impostor` impostors), the configured `sensitivity` (the DTW tolerance, formerly `dtw_tolerance`) and `sessions_per_user`.

- **Profile:** a legitimate user's first `sessions_per_user` sessions.
- **Tested sessions:** every user's next 2 sessions after that (never in a profile; the same count as script 15).
- **Accuracy per user:** legitimate = share of the user's own tested sessions that match their own profile; impostor = share of the impostor's tested sessions that no legitimate profile matches. A legitimate user is **accepted** (an impostor **goes through**) when at least `match_session_ratio` of those sessions match (a session matches when at least `match_shape_ratio` of its strokes match).

```bash
.venv/bin/python experiment_earl/src/09_find_sensitivity.py     # seconds once the DTW cache is warm
```

Outputs, inside the run folder: `results/sensitivity/users.csv` (one row per user: role, accuracy, sessions correct, accepted/through, which profiles matched), `results/sensitivity/summary.csv` (legitimate accepted, impostors through, both accuracies, their mean, `impostor_sensitivity`) and `figures/find_sensitivity.png`: two separate graphs, **legitimate** (x = each legitimate user) and **impostor** (x = each impostor), y = accuracy, one line per sensitivity. To try another sensitivity, change `sensitivity` and rerun: each value gets its own run folder.

### F. Find the sessions (User × Session × Sensitivity) and the sensitivity heatmap

Same users and tested sessions as E, at the sensitivity E used (read from `results/sensitivity/summary.csv`, so run E first), with 1, 2, … `sessions_per_user` profile sessions (each step contains the one before).

```bash
.venv/bin/python experiment_earl/src/10_find_session.py
```

Outputs, inside the run folder: `results/session/{users,summary,heatmap}.csv`, `figures/find_session.png` (the same two graphs, one line per session count) and `figures/sensitivity_heatmap.png` (profile sessions × number of legitimate users, the first 1 … `n_legitimate` of the draw as in the notebook; colour = **sensitivity** = impostors through / impostors, the former threshold, 0–1 in 0.1 steps).

**Results so far:** with the adviser's tolerances 0.2–1.0 (earlier version of these scripts) every legitimate user was accepted and every impostor went through. At `sensitivity` 0.02 (`oct14_exp1_c8f010`, user20 vs user21, user23, user29, user35, 1–2 sessions) it is the opposite: no impostor gets through, but user20's own sessions are rejected too (accuracy 0.50).

### G. Matched shapes### J. Matched shapes behind the per-user bar graphs

Shows which impostor strokes matched which strokes of each legitimate user in the notebook (A): the same draw, users and sessions, one figure per legitimate user and session step. Each panel is one matched pair after normalization (what DTW compares): the impostor stroke (red dashed) on the user's stroke it matched (blue), with both session ids, chunk numbers and the DTW cost per point. The figure title repeats the bar graph's verdict per impostor (strokes matched, sessions at or above `match_shape_ratio`, matched or not). Run the notebook first so the run folder exists.

```bash
.venv/bin/python experiment_earl/src/14_plot_matches.py --run oct12_test2_d4015c                  # all users and steps, ~2 minutes
.venv/bin/python experiment_earl/src/14_plot_matches.py --run oct12_test2_d4015c --user user9 --sessions 2
.venv/bin/python experiment_earl/src/14_plot_matches.py --max 60                                   # more pairs per figure
```

Outputs, inside the run folder: `figures/matches/<user>_sessions<k>.png` (at most `--max` pairs, random sample) and `results/matches.csv` (every matched stroke of the drawn users and steps).

### H. Genuine check: own unused sessions against their own profile

The notebook (A) only asks whether impostors get through. This asks the opposite: does a legitimate user's own new session match their own profile? Same draw, same profiles (first 1, 2, ... `sessions_per_user` sessions) and the same `match_shape_ratio` rule. Each legitimate user's next `--held-out` sessions after the first `sessions_per_user` (default 2; never part of the profile at any step) are tested, next to the impostors' sessions against the same profile.

```bash
.venv/bin/python experiment_earl/src/15_genuine_check.py --run oct12_test3_d05fb2       # seconds once the DTW cache is warm
.venv/bin/python experiment_earl/src/15_genuine_check.py --held-out 5                    # more own sessions per user
```

Outputs, inside the run folder: `results/genuine_check.csv` (every tested session: share of strokes matched, passed or not), `results/genuine_check_summary.csv` and `figures/genuine_check.png` (one panel per legitimate user: own sessions blue, impostors red, label = sessions passed / tested).

### Working with an older run

Every script takes `--run <run folder>` (its path under `runs/`). It then uses that folder and the settings saved in it, whatever `config.yaml` says now:

```bash
.venv/bin/python experiment_earl/src/07_plot_shapes.py --run 1a2b3c/1_9_0.04_10 --user user12
.venv/bin/python experiment_earl/src/08_run_notebook.py --run 1a2b3c/1_9_0.02_10
```

Run folders are `<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>`: the hash covers every other setting (seed, chunking, matching, ...), so runs that differ only in those four sit side by side under one hash. Runs made before 2026-10-15 are flat `<run_name>_<hash>` folders and still open with `--run`. Runs made before 2026-10-08 used training files only; runs before 2026-10-14 read the separate `training_files`/`test_files` folders.

## 4. Where the results are

```
experiment_earl/runs/<hash>/<L>_<I>_<sensitivity>_<sessions>/
├── config.yaml          the exact settings this run used
├── run.json             when the folder was created and the git commit
├── notebooks/           executed notebook with all tables and plots                (A)
├── figures/
│   ├── session_progression.png          bar graph: impostors matched per session step   (A)
│   ├── session_progression_users.png    one bar graph per legitimate user               (A)
│   ├── session_progression_heatmap.png  heatmap: sessions × legitimate users            (A)
│   ├── sweep_heatmaps.png               one heatmap per session count                   (B)
│   ├── sweep_lines.png                  sensitivity vs sessions / legitimate / impostors (B)
│   ├── find_sensitivity.png             accuracy per legitimate user and per impostor (E)
│   ├── find_session.png                 same, one line per session count               (F)
│   ├── sensitivity_heatmap.png          sessions × legitimate users, colour = sensitivity (F)
│   ├── matches/<user>_sessions<k>.png   matched impostor strokes on the user's strokes  (G)
│   └── genuine_check.png                own unused sessions vs impostors, per profile   (H)
├── results/
│   ├── session_progression.csv          one row per session step                        (A)
│   ├── session_progression_steps.csv    every step, every impostor                      (A)
│   ├── session_progression_heatmap.csv  the heatmap's numbers                           (A)
│   ├── session_progression_users.csv    impostors matched per legitimate user and step  (A)
│   ├── sweep/summary.csv                every combination: matched and sensitivity      (B)
│   ├── sweep/saturation.csv             where each curve flattens and jumps             (B)
│   ├── trial_0.json                     per-impostor and held-out match ratios          (C)
│   ├── summary.csv                      sensitivity of the single trial                 (C)
│   ├── sensitivity/{users,summary}.csv  per user and overall, at the sensitivity       (E)
│   └── session/{users,summary,heatmap}.csv  per user / per session count / heatmap   (F)
├── results/matches.csv    every matched stroke behind the per-user bar graphs      (G)
├── results/genuine_check{,_summary}.csv  own unused sessions vs impostors     (H)
├── shapes/              chunks (.npz) and chunk PNGs                                (C, D)
└── temp/                drawn sessions and manifest.json                           (C)
```

How to read them:

- **Impostors matched**: how many impostor users looked like a legitimate user. Lower is better.
- **Sensitivity** (called *threshold* before 2026-10-14) = impostors matched / impostor users, from 0 to 1. 0 is best: no impostor passed. In E and F, *sensitivity* also names the DTW tolerance being tried (config key `sensitivity`); the CSVs call the share `impostor_sensitivity`.
- **Accuracy** (E, F): per user, the share of tested sessions decided correctly (own sessions matched, impostor sessions rejected); overall, legitimate users accepted / legitimate users and impostors kept out / impostors.
- **±** (std, sweep only): how much a sweep cell changes from draw to draw. It is blank (NaN) when `n_trials` is 1, because one draw has no spread. The notebook, E and F use one fixed draw, so they have no ±.

The whole `runs/` folder is git-ignored: results stay on your computer. Copy a run folder to share it.

## 5. How long it takes

For the scripts (01–07), the first run of a new chunking or matching setting is the slowest, because every shape comparison (DTW) is computed once and then cached in `experiment_earl/cache/` for all later runs. The notebook keeps its own cache only while it runs, so every notebook run takes about the same time.

| What | Typical time |
|---|---|
| Notebook, 6 + 2 users, 1–5 sessions | about 1–2 minutes |
| Matched shapes (G), 6 users × 5 steps | about 2 minutes |
| Sweep, 1–5 sessions, 20 draws, first time | about 30 minutes; reruns that only redraw the figures take seconds |
| Single trial 01–05 | a few minutes (step 04 also scores the held-out sessions) |
| Find the sensitivity (E) and the sessions (F) | seconds once the DTW cache is warm; a new `sensitivity` takes about a minute |
| Shape PNGs (D) for 10 users × 5 sessions | about 25 minutes (about 44,000 images) |

More sessions per user means more shapes to compare, so runs beyond 5 sessions take noticeably longer.

## 6. Common problems

| Message | Fix |
|---|---|
| `... users do not fit in the 10 Balabit users` | Lower `n_legitimate` or `n_impostor`: they must add up to 10 or less. |
| `sessions_per_user = N but some user has only M sessions` | Lower `sessions_per_user` to M or less (114). |
| `sweep_sessions_max = N but some user has only M sessions` | Same for the sweep's `sweep_sessions_max`. |
| `KeyError` in the sweep right after the draws | `n_trials` is 0; set it to at least 1. |
| `No run '...' under .../runs` | The `--run` name is wrong; the message lists the existing runs. |
| `ModuleNotFoundError: numba` (or `nbformat`) | Use `.venv/bin/python`, or redo the setup in section 1. |
| `'RcParams' object has no attribute '_get'` | Run `.venv/bin/pip install "matplotlib-inline<0.2"`. |
| `Run ... has no shapes yet` from `07_plot_shapes.py` | That run only has notebook results. Run steps 01–03 with the same `--run` (the message prints the commands), then export. |
| `No .../results/sensitivity/summary.csv; run 09_find_sensitivity.py first` | Run E before F (same config or `--run`). |
| `Need N sessions per user (sessions_per_user + 2 tested)` | Lower `sessions_per_user` (at most 112). |
| `No shapes for userX in run ...` | That user was not drawn in this run's single trial; the message lists the users that have shapes. |
