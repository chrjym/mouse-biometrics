# How to run the EARL simulation notebook

`earl_simulation.ipynb` (in this folder) runs every simulation of the EARL shape-matching experiment: the batch of
runs, accuracy, the best setting per split, the sensitivity sweep and the best setting per user. You set everything
in one cell and press **Run All**. It writes **CSV files only**; there are no figures yet.

It replaces the Python scripts in `experiment_earl/src/` (adviser, 2026-10-26) and gives the same results: on a
small test every CSV was identical to the scripts' output.

## Contents

1. [One-time setup](#1-one-time-setup)
2. [Open the notebook](#2-open-the-notebook)
3. [Change the settings](#3-change-the-settings)
4. [Run it](#4-run-it)
5. [Where the results are](#5-where-the-results-are)
6. [How long it takes](#6-how-long-it-takes)
7. [Common problems](#7-common-problems)

---

## 1. One-time setup

This is the only part that needs a terminal, and only once per machine. Run it from the repository root
(`thesis-mouse-biometrics/`).

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install nbformat nbconvert ipykernel "matplotlib-inline<0.2"
```

On Windows, use `.venv\Scripts\pip` instead of `.venv/bin/pip`.

The notebook needs **numba** (fast shape matching), which only the `.venv` has. If you will use Jupyter (not
VS Code), also register the `.venv` as a kernel so Jupyter can find it:

```bash
.venv/bin/python -m ipykernel install --user --name earl-venv --display-name ".venv (EARL)"
```

The Balabit data is already in the repository (`experiment_earl/datasets/`); nothing to download.

## 2. Open the notebook

Pick the way that matches where you run it.

### On your own computer, in VS Code

1. Open the repository folder in VS Code.
2. Open `experiment_earl/notebooks/earl_simulation.ipynb`.
3. Top right, click **Select Kernel** and choose the `.venv` environment.

### On your own computer, in Jupyter

```bash
.venv/bin/jupyter lab
```

Open `experiment_earl/notebooks/earl_simulation.ipynb`, then **Kernel → Change Kernel → .venv (EARL)**.

### On another machine or a remote server

On the server (once per session), start Jupyter inside `tmux` so it keeps running when you disconnect:

```bash
tmux new -s earl
cd thesis-mouse-biometrics
.venv/bin/jupyter lab --no-browser --port 8888
```

Detach with `Ctrl+B`, then `D`. On your own computer, open a tunnel and visit the link Jupyter printed (it starts
with `http://localhost:8888/...`):

```bash
ssh -L 8888:localhost:8888 <user>@<server>
```

Then open the notebook and pick the **.venv (EARL)** kernel as above. Closing the browser does not stop a running
simulation; stopping the server or the kernel does (see section 7).

## 3. Change the settings

Everything you can change is in the **Settings** cell, near the top. Do not edit the other cells.

| Block | What it controls |
|---|---|
| `SETTINGS` | The experiment itself: `seed` (which users and sessions are drawn), the data folder, how sessions are cut into strokes (`pause_gap_s`, `min_points`, `min_length_px`, `resample_n`) and how they are matched (`dtw_band`, `match_shape_ratio`, `match_session_ratio`). These values name the results folder. |
| `BATCH` | Which runs the batch simulates: every `splits` × `sensitivities` × `sessions` combination is one run. `session_progression: False` skips the step-by-step impostor counts and is faster. |
| `SKIP_FINISHED_RUNS` | `True` = runs that already have results are not simulated again. |
| `SWEEP` | The sensitivity sweep: its fixed splits, the sensitivities scored (start, stop, step), the library sizes and the sessions tested per user. |
| `SINGLE_RUN`, `GENUINE_HELD_OUT` | The one run used by the two optional checks (matched pairs, genuine check). |
| `SECTIONS` | Switch each section on (`True`) or off (`False`). |

Limits (the notebook checks these and stops with a message if one is broken):

- A split uses at most **10 users** in total (Balabit has 10).
- After the attack sessions are dropped, every user has at least **87 sessions**. So `BATCH` sessions can go up to
  **43** (a user's tested sessions must not overlap their profile), and `SWEEP` `sessions_max + test_sessions` up
  to **87**.

**Try it small first.** The default batch is 6,750 runs and takes many hours. For a first run, use for example:

```python
"splits": [[1, 9], [5, 5]],
"sensitivities": [0.02, 0.05],
"sessions": [2, 4],
```

## 4. Run it

Press **Run All** (VS Code: *Run All* at the top; Jupyter: *Run → Run All Cells*). The sections run top to bottom:

| Section | What it does | Needs |
|---|---|---|
| 1. Shared code | Loads the code and the saved DTW results | – |
| 2. Data check | Counts users and sessions, checks the settings fit | – |
| 3. Batch | Simulates every run of `BATCH`; prints one line per run | – |
| 4. Accuracy | Collects every finished run into one table and a summary | 3 |
| 5. Best per split | Best sensitivity and sessions per split | 4 |
| 6. Sensitivity sweep | One confusion matrix per split, library size and sensitivity | – |
| 7. Best setting per user | Best setting per legitimate user, checked on unseen sessions | 6 |
| 8. Matched pairs (off by default) | Which impostor strokes matched which user strokes | – |
| 9. Genuine check (off by default) | A user's own unused sessions against their own profile | – |

Each section prints what it wrote (`Output: ...`). To run only some sections, switch the others off in `SECTIONS`
and press Run All again.

## 5. Where the results are

Everything goes to `experiment_earl/runs/<hash>/`. The 6-character `<hash>` is made from `SETTINGS`: the same
settings always use the same folder, and changing any of them starts a new folder, so earlier results are never
overwritten. The default settings use `runs/19399f/`.

```
experiment_earl/runs/
├── batch_log.csv                         every batch run: time, status, seconds, error
└── <hash>/
    ├── <L>_<I>_<sensitivity>_<sessions>/ one folder per batch run, e.g. 1_9_0.02_10/
    │   ├── config.yaml, run.json         the run's settings, when it was made
    │   └── results/
    │       ├── accuracy.csv              per user: sessions passed / tested, through or not
    │       └── session_progression*.csv  impostors matched per session step (if switched on)
    ├── accuracy.csv                      every run and user together                  (4)
    ├── summary/summary.csv               one row per run                              (4)
    ├── best/                             scores.csv, best.csv, best_rows.csv          (5)
    └── sweep/
        ├── confusion.csv                 per split, library size and sensitivity      (6)
        ├── user_confusion.csv            the same per legitimate user                 (6)
        ├── parts/, config.yaml           finished splits and the sweep's settings     (6)
        └── best/                         best_users.csv, best_splits.csv              (7)
```

The two optional checks write `results/matches.csv` and `results/genuine_check{,_summary}.csv` into the
`SINGLE_RUN` folder. `runs/` and `cache/` are not committed to git: copy a folder if you need to share it.

## 6. How long it takes

- **Small test** (2 splits, 2 sensitivities, 2 session counts, small sweep): about 15 seconds.
- **Sensitivity sweep** with the default settings: a few minutes the first time; seconds afterwards, because the
  DTW distances are saved in `experiment_earl/cache/distances.pkl`.
- **Full default batch** (6,750 runs): many hours. The old script version took about 40 hours; the notebook reuses
  DTW results between runs of the same sensitivity, so it should be faster, but this has not been measured yet.

More sessions per user means more strokes to compare, so runs with many sessions take noticeably longer. A machine
with more CPU cores runs the matching faster.

## 7. Common problems

| Message or situation | What to do |
|---|---|
| `ImportError: numba is not installed in this kernel` | The wrong kernel is selected. Choose the `.venv` kernel (section 2). |
| `FileNotFoundError: No datasets/balabit found` | The notebook was opened from outside the repository. Open it from `experiment_earl/notebooks/`. |
| `ValueError: Settings do not fit the data` | The message lists what to change in the Settings cell (section 3, limits). |
| `No finished runs ...: run section 3 first` | Switch `"batch"` on, or check that `SETTINGS` is the same as when the runs were made. |
| A batch run shows `failed` | The error is printed and saved in `runs/batch_log.csv`; the batch continues with the next run. |
| The server or kernel stopped in the middle of a batch | Open the notebook again and press Run All. With `SKIP_FINISHED_RUNS = True`, finished runs are skipped and only the rest is simulated. It does **not** restart by itself. |
| Results land in a new `runs/<hash>/` folder | A value in `SETTINGS` differs from before. Put it back to reuse the old folder. |
| Kernel dies on a very large batch | Out of memory. Run fewer sensitivities at a time; finished runs are kept. |
