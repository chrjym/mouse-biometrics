# How to run the EARL simulation notebook

`earl_simulation.ipynb` (in this folder) runs every simulation of the EARL shape-matching experiment: the batch of
runs, accuracy, the best setting per split, the sensitivity sweep and the adviser's experiments 1 and 2. You set
everything in one cell and press **Run All**. It writes **CSV files**, plus the two figures of experiments 1 and 2.

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
| `EXPERIMENTS` | Experiments 1 and 2 (adviser, Thesis Consultation v6): the four splits as `[legitimate, impostor]` (1 x 5, 5 x 1, 3 x 2, 2 x 3 as I x L), experiment 1's sensitivities (start, stop, step) and session count, experiment 2's session counts (start, stop, step). |
| `STROKES` | Stroke export (section 10): `users` = the users whose strokes are written, one CSV per session with one row per stroke (kind, points, timing, start/end position, size, path length, straightness, speed). `None` = all 10 users, or a list such as `["user7", "user29"]`. |
| `SECTIONS` | Switch each section on (`True`) or off (`False`). |

Limits (the notebook checks these and stops with a message if one is broken):

- A split uses at most **10 users** in total (Balabit has 10).
- After the attack sessions are dropped, every user has at least **87 sessions**. So `BATCH` sessions can go up to
  **43** (a user's tested sessions must not overlap their profile), and `SWEEP` `sessions_max + test_sessions` up
  to **87**.

**Try it small first.** The default batch is 4 splits × 100 sensitivities × 8 session counts = 3,200 runs (about
10 minutes on 2 cores). For a first run, use for example:

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
| 7. Matched pairs (off by default) | Which impostor strokes matched which user strokes | – |
| 8. Genuine check (off by default) | A user's own unused sessions against their own profile | – |
| 9. Experiments 1 and 2 | Experiment 1: accuracy against sensitivity at 1 session; experiment 2: accuracy against sessions at experiment 1's best sensitivity. Legitimate and impostor graph, one confusion matrix each (positive = impostor, session counts added up to the last iteration), the best point marked with a "best" arrow. Missing runs are simulated. | – |

Each section prints what it wrote (`Output: ...`). To run only some sections, switch the others off in `SECTIONS`
and press Run All again.

### Long runs: start it from the Jupyter terminal (recommended by the adviser)

Run All in the browser is fine for short runs. For a batch that takes hours, start the notebook from the terminal
that JupyterLab has built in. It then keeps running on the server after you close the terminal tab or the browser.

1. Edit the Settings cell and **save the notebook** (`Ctrl+S`). The terminal run reads the saved file, not what is
   on your screen.
2. Open a terminal inside Jupyter: **File → New → Terminal** (or the *Terminal* tile in the Launcher). It is a shell
   on the server, in the folder Jupyter was started from. If that is not the repository root, `cd` into it first.
3. Start the run in the background:

   ```bash
   mkdir -p experiment_earl/runs
   nohup .venv/bin/jupyter execute experiment_earl/notebooks/earl_simulation.ipynb > experiment_earl/runs/notebook_run.log 2>&1 &
   echo $! > experiment_earl/runs/notebook_run.pid
   ```

   `nohup ... &` keeps it running after the tab closes; the messages go to `notebook_run.log`. The terminal prints
   the run's process ID (PID), e.g. `[1] 90133`, and the second line saves it to `notebook_run.pid`, so you can
   find it again from a new terminal tab.
4. **Watch it live.** The terminal itself shows nothing while the notebook runs, but everything the notebook prints
   (each batch run, each sweep split, every `Output:` line, the best settings) is also written to a progress file.
   Follow it with:

   ```bash
   tail -f experiment_earl/runs/notebook_progress.log    # Ctrl+C stops watching; the run goes on
   ```

   Each start adds a `=== <date time> notebook started ===` line, so earlier runs stay above it. Every line has a
   time, and long sections say what they are doing right now, for example:

   ```
   10:32:11  ==== 3. Batch ====
   10:32:11  [1/60] 540c32/1_9_0.02_10: started (1 legitimate + 9 impostors, sensitivity 0.02, 10 sessions per user)
   10:32:11    legitimate: user16 | impostors: user15, user23, ...
   10:32:12    session progression: 4/10 sessions per user
   10:32:40    accuracy: impostor user23 (2/9) against 1 library
   10:33:05  [1/60] 540c32/1_9_0.02_10 ... ok (0m 54s), about 53m 06s left
   10:45:00  ==== 6. Sensitivity sweep ====
   10:45:00  [1 L, 5 I] started
   10:45:30      impostor user15: 20/40 sessions tested against 1 library
   ```

   For a one-line-per-run table of the batch, `experiment_earl/runs/batch_log.csv` is still written too.

   **Everything at once:** `status.sh` shows whether the run is still going (PID, time running, CPU and memory of
   the runner and its kernel), the error if it stopped on one, how many batch runs are logged, and the latest
   progress lines:

   ```bash
   bash experiment_earl/notebooks/status.sh          # last 20 progress lines; add a number for more, e.g. 50
   watch -n 5 bash experiment_earl/notebooks/status.sh   # refresh every 5 s; Ctrl+C stops watching
   ```

5. **See the process (PID) and whether it is still running.** A run is two processes: the runner, whose PID was
   saved above, and the kernel that does the computing (a child of the runner).

   ```bash
   PID=$(cat experiment_earl/runs/notebook_run.pid)
   ps -o pid,etime,%cpu,%mem,cmd -p $PID           # the runner: PID, time running, CPU, memory
   ps -o pid,etime,%cpu,%mem -p $(pgrep -P $PID)  # the kernel doing the work
   top -p $(pgrep -P $PID)                         # live CPU and memory of the kernel; q to quit
   pgrep -af jupyter-execute                       # every notebook run on this machine
   ```

   If `ps -p $PID` prints only the header line, the run has finished. If a cell failed, the run stopped there and the
   error is at the end of the log: `tail -20 experiment_earl/runs/notebook_run.log`. The results are where section 5
   says.
6. **Stop it early:** `kill $(cat experiment_earl/runs/notebook_run.pid)`. Its kernel shuts down with it, and
   finished runs are kept.

Do not start a second run of the notebook (terminal or browser) while one is going: both would write the same
files. A run started this way does not restart by itself if the server is restarted.

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
    ├── sweep/
    │   ├── confusion.csv                 per split, library size and sensitivity      (6)
    │   ├── user_confusion.csv            the same per legitimate user                 (6)
    │   └── parts/, config.yaml           finished splits and the sweep's settings     (6)
    ├── experiments/                      exp1/exp2: _points.csv (per split and point: counts, running totals),
    │                                     _overall.csv (all splits per point, best = True), _confusion.csv, .png  (9)
    └── strokes/                          <user>/<session>.csv (one row per stroke), all_strokes.csv,
                                          sessions.csv (one row per session)                                  (10)
```

The two optional checks write `results/matches.csv` and `results/genuine_check{,_summary}.csv` into the
`SINGLE_RUN` folder. `runs/` and `cache/` are not committed to git: copy a folder if you need to share it.

## 6. How long it takes

- **Small test** (2 splits, 2 sensitivities, 2 session counts, small sweep): about 15 seconds.
- **Full default batch** (3,200 runs, 2 cores, measured 2026-10-28): about 9 minutes the first time, of which about
  4 are the DTW costs of the 28,800 session pairs. Each pair is compared once; every run and sensitivity reuses its
  cost (`experiment_earl/cache/costs.pkl`), and the session progression is computed once per sensitivity and split.
- **Sensitivity sweep and experiments 1 and 2:** seconds, because they reuse the batch's DTW costs (a few minutes
  if they run without the batch first).

More sessions per user means more strokes to compare, so runs with many sessions take noticeably longer. A machine
with more CPU cores runs the matching faster.

## 7. Common problems

| Message or situation | What to do |
|---|---|
| `ImportError: numba is not installed in this kernel` | The wrong kernel is selected. Choose the `.venv` kernel (section 2). |
| `FileNotFoundError: No datasets/balabit found` | The notebook was opened from outside the repository. Open it from `experiment_earl/notebooks/`. |
| `ValueError: Settings do not fit the data` | The message lists what to change in the Settings cell (section 3, limits). |
| `No finished runs ...: run section 3 first` | Switch `"batch"` on, or check that `SETTINGS` is the same as when the runs were made. |
| Started from the terminal and nothing appears | Normal: the terminal shows nothing in that mode. Watch `tail -f experiment_earl/runs/notebook_progress.log`, and check `pgrep -af jupyter-execute` (section 4). |
| Terminal: `No such file or directory: .venv/bin/jupyter` | The terminal is not in the repository root. `cd` into the repository folder and start again. |
| A batch run shows `failed` | The error is printed and saved in `runs/batch_log.csv`; the batch continues with the next run. |
| The server or kernel stopped in the middle of a batch | Open the notebook again and press Run All. With `SKIP_FINISHED_RUNS = True`, finished runs are skipped and only the rest is simulated. It does **not** restart by itself. |
| Results land in a new `runs/<hash>/` folder | A value in `SETTINGS` differs from before. Put it back to reuse the old folder. |
| Kernel dies on a very large batch | Out of memory. Run fewer sensitivities at a time; finished runs are kept. |
