# How to run simulation.ipynb on the server

`simulation.ipynb` runs every simulation of the EARL shape-matching experiment: the batch of runs, accuracy, the
best setting per split, the sensitivity sweep and the adviser's experiments 1 and 2. You change one Settings cell and
run the whole notebook. It writes **CSV files**, plus the two figures of experiments 1 and 2.

It is the server copy of `experiment_earl/notebooks/earl_simulation.ipynb`: the simulation code and settings are the
same, only the setup is different (it finds its folders on the server, installs missing packages, and writes a
progress log).

## Contents

1. [What goes where](#1-what-goes-where)
2. [Copy the files to the server (once)](#2-copy-the-files-to-the-server-once)
3. [Set up Python (once)](#3-set-up-python-once)
4. [Open the notebook](#4-open-the-notebook)
5. [Change the settings](#5-change-the-settings)
6. [Run it](#6-run-it)
7. [Watch a long run](#7-watch-a-long-run)
8. [Where the results are](#8-where-the-results-are)
9. [How long it takes](#9-how-long-it-takes)
10. [Common problems](#10-common-problems)

---

## 1. What goes where

Everything lives in one folder on the server, `experiment/`:

```
experiment/
├── simulation.ipynb          the notebook
├── HOW_TO_RUN.md             this guide
├── requirements.txt          the Python packages
├── status.sh                 shows whether a run is going and its latest progress
├── .venv/                    Python environment (step 3)
├── datasets/balabit/         the Balabit data (step 2)
└── experiment_earl/
    ├── runs/                 every result and log (made by the notebook)
    └── cache/                saved DTW results, reused by later runs (made by the notebook)
```

**Every command in this guide runs inside `experiment/`** unless it says "on your own computer". If a command
says `No such file or directory`, first run `cd ~/experiment` (or wherever the folder is).

## 2. Copy the files to the server (once)

On your own computer, from the repository root (`thesis-mouse-biometrics/`). Replace `<user>@<server>` with your
login, e.g. `earl@10.0.0.5`.

```bash
# the notebook and its helpers
scp experiment_earl/server/{simulation.ipynb,requirements.txt,HOW_TO_RUN.md,status.sh} <user>@<server>:experiment/

# the Balabit data (~200 MB; only needed once)
rsync -a experiment_earl/datasets <user>@<server>:experiment/
```

The notebook looks for the data in `experiment/datasets/balabit/` first, then in
`experiment/experiment_earl/datasets/balabit/`; either place works. If you uploaded `datasets.zip` instead, unzip it on
the server so that `experiment/datasets/balabit/users/` exists (`cd experiment && unzip ../datasets.zip`, then check
with `ls datasets/balabit/users`). The notebook prints the folder it uses as `data folder: ...`.

Optional: if you already ran simulations on your computer with the same settings, copy the DTW cache too, so the
server does not compute those distances again:

```bash
rsync -a experiment_earl/cache <user>@<server>:experiment/experiment_earl/
```

When you change `simulation.ipynb` on your computer, copy it again with the first `scp` line. The data does not
need to be copied again.

## 3. Set up Python (once)

Log in to the server (`ssh <user>@<server>`), then:

```bash
cd experiment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ipykernel install --user --name earl-venv --display-name ".venv (EARL)"
```

- The first line makes a private Python environment in `.venv/`, so nothing is installed system-wide.
- The second installs numpy, pandas, pyyaml, matplotlib, **numba** (the fast shape matching) and Jupyter. The
  server has Python 3.14, which needs numba 0.63 or newer; pip picks the right one.
- The third registers `.venv` as a Jupyter kernel named **.venv (EARL)**.

Check it worked:

```bash
.venv/bin/python -c "import numba, pandas; print('numba', numba.__version__)"
```

If you forget this step, the notebook's first code cell tries to install any missing package into whatever kernel
you opened it with. That fails on Ubuntu's system Python, so use the `.venv` kernel.

## 4. Open the notebook

You only need this to edit settings or to run short tests in the browser. Long runs are started from a terminal
(section 6) and do not need the browser open.

On the server, start Jupyter inside `tmux`, so it keeps running when you disconnect:

```bash
tmux new -s earl
cd ~/experiment
.venv/bin/jupyter lab --no-browser --port 8888
```

Leave tmux running with `Ctrl+B`, then `D` (`tmux attach -t earl` brings it back). Jupyter prints a link that
starts with `http://localhost:8888/lab?token=...`; copy it.

On your own computer, open a tunnel to the server and keep this terminal open:

```bash
ssh -L 8888:localhost:8888 <user>@<server>
```

Paste the link into your browser, open `simulation.ipynb`, and pick **Kernel → Change Kernel → .venv (EARL)**.

## 5. Change the settings

Everything you can change is in the **Settings** cell near the top. Do not edit the other cells.

| Block | What it controls |
|---|---|
| `SETTINGS` | The experiment itself: `seed` (which users and sessions are drawn), the data folder, how sessions are cut into strokes (`pause_gap_s`, `min_points`, `min_length_px`, `resample_n`) and how they are matched (`dtw_band`, `match_shape_ratio`, `match_session_ratio`). These values name the results folder. |
| `BATCH` | Which runs section 3 simulates: every `splits` × `sensitivities` × `sessions` combination is one run. `session_progression: False` skips the step-by-step impostor counts and is faster. |
| `SKIP_FINISHED_RUNS` | `True` = runs that already have results are not simulated again. Keep it `True`. |
| `SWEEP` | The sensitivity sweep (section 6): its fixed splits, the sensitivities scored (start, stop, step), the library sizes and the sessions tested per user. |
| `EXPERIMENTS` | Experiments 1 and 2 (section 9): the four splits, experiment 1's sensitivities (start, stop, step) and session count, experiment 2's session counts (start, stop, step). |
| `SINGLE_RUN`, `GENUINE_HELD_OUT` | The one run used by the two optional checks (sections 7 and 8). |
| `CORES` | CPU cores the matching may use: `2`, the cores the adviser gave us. A container often shows every core of the host, and using more threads than our share only slows it down. The data check prints `numba uses 2 CPU cores`. Not part of the results folder name. |
| `SECTIONS` | Switch each section on (`True`) or off (`False`). |

Limits (the notebook checks them and stops with a message that says what to change):

- A split uses at most **10 users** in total (Balabit has 10).
- Every user has at least **87 sessions** after the attack sessions are dropped. So `BATCH` sessions can go up to
  **43**, and `SWEEP` `sessions_max + test_sessions` up to **87**.

**Try it small first.** The current batch is 4 splits × 100 sensitivities × 8 session counts = 3,200 runs, which
takes many hours. For a first test, set for example:

```python
"splits": [[1, 2]],
"sensitivities": [0.05],
"sessions": [2],
```

and switch `"sweep"` and `"experiments"` off in `SECTIONS`. That finishes in under a minute.

**Save the notebook (`Ctrl+S`) after every change.** A run started from the terminal reads the saved file, not what
is on your screen.

## 6. Run it

### Short runs: in the browser

Press **Run → Run All Cells**. The sections run top to bottom and each prints what it wrote (`Output: ...`).
Closing the browser tab stops nothing, but stopping Jupyter or the kernel stops the run.

### Long runs: from the terminal (recommended)

This keeps running on the server after you close the browser, the terminal, or your laptop. Use the JupyterLab
terminal (**File → New → Terminal**) or a plain `ssh` session:

```bash
cd ~/experiment
mkdir -p experiment_earl/runs
nohup .venv/bin/jupyter execute simulation.ipynb > experiment_earl/runs/notebook_run.log 2>&1 &
echo $! > experiment_earl/runs/notebook_run.pid
```

- `nohup ... &` runs it in the background and keeps it alive when you log out.
- `notebook_run.log` gets Jupyter's own messages and, if the run fails, the error.
- `notebook_run.pid` saves the process number, so `status.sh` and the stop command can find it later.

The terminal prints nothing more while the notebook runs; that is normal. Section 7 shows how to watch it.

**Run one at a time.** Two runs at once (terminal or browser) write the same files. Check first with
`bash status.sh`.

### What the sections do

| Section | What it does | Needs |
|---|---|---|
| 1. Shared code | Loads the code and the saved DTW results | – |
| 2. Data check | Counts users and sessions, checks that the settings fit | – |
| 3. Batch | Simulates every run of `BATCH`, one line per run | – |
| 4. Accuracy | Collects every finished run into one table and a summary | 3 |
| 5. Best per split | Best sensitivity and sessions per split | 4 |
| 6. Sensitivity sweep | One confusion matrix per split, library size and sensitivity | – |
| 7. Matched pairs (off by default) | Which impostor strokes matched which user strokes | – |
| 8. Genuine check (off by default) | A user's own unused sessions against their own profile | – |
| 9. Experiments 1 and 2 | Accuracy against sensitivity (exp 1) and against sessions at exp 1's best sensitivity (exp 2), with confusion matrices and two figures. Missing runs are simulated. | – |

## 7. Watch a long run

```bash
tail -f experiment_earl/runs/notebook_progress.log   # live; Ctrl+C stops watching, the run goes on
```

Everything the notebook prints is copied to this file. Each start adds a `=== <date time> notebook started ===`
line, and every batch run adds a line with its time, for example:

```
=== 2026-10-27 14:01:14 notebook started, progress also in .../experiment_earl/runs/notebook_progress.log ===
10 users, 1,271 sessions; every user has at least 87
3,200 runs in the plan, 0 finished earlier, 3,200 to run
14:01:14  [1/3200] 19399f/5_1_0.01_5 ... ok (0m 41s)
```

For everything at once:

```bash
bash status.sh                  # running or not, PID, time running, CPU and memory, error if it stopped, last 20 lines
bash status.sh 50               # last 50 lines
watch -n 5 bash status.sh       # refresh every 5 s; Ctrl+C stops watching
```

`RUNNING (PID ...)` means it is still going. `NOT RUNNING` means it finished or stopped; if it stopped on an error,
`status.sh` prints the error. The full error is at the end of `experiment_earl/runs/notebook_run.log`.

Stop a run early:

```bash
kill $(cat experiment_earl/runs/notebook_run.pid)
```

Finished runs are kept. Start it again with the commands of section 6: with `SKIP_FINISHED_RUNS = True` it only
simulates what is missing. The same applies after a server restart; nothing restarts by itself.

## 8. Where the results are

Everything goes to `experiment_earl/runs/<hash>/`. The 6-character `<hash>` is made from `SETTINGS`: the same
settings always use the same folder, and changing any of them starts a new folder, so earlier results are never
overwritten. The hash is the same on the server and on your computer.

```
experiment_earl/runs/
├── notebook_progress.log, notebook_run.log, notebook_run.pid   logs of terminal runs
├── batch_log.csv                         every batch run: time, status, seconds, error
└── <hash>/
    ├── <L>_<I>_<sensitivity>_<sessions>/ one folder per batch run, e.g. 5_1_0.05_10/
    │   ├── config.yaml, run.json         the run's settings, when it was made
    │   └── results/
    │       ├── accuracy.csv              per user: sessions passed / tested, through or not
    │       └── session_progression*.csv  impostors matched per session step (if switched on)
    ├── accuracy.csv                      every run and user together                        (section 4)
    ├── summary/summary.csv               one row per run                                    (4)
    ├── best/                             scores.csv, best.csv, best_rows.csv                (5)
    ├── sweep/                            confusion.csv, user_confusion.csv, parts/          (6)
    └── experiments/                      exp1/exp2 _points.csv, _overall.csv, _confusion.csv, .png  (9)
```

Copy the results back to your own computer (on your own computer, from the repository root):

```bash
rsync -a <user>@<server>:experiment/experiment_earl/runs/ experiment_earl/runs/
```

## 9. How long it takes

- **Small test** (section 5): under a minute.
- **Sensitivity sweep**: a few minutes the first time; seconds afterwards, because the DTW distances are saved in
  `experiment_earl/cache/`.
- **Full batch** (thousands of runs): many hours. Runs with more sessions per user take longer. The matching uses
  every CPU core of the server.

## 10. Common problems

| Message or situation | What to do |
|---|---|
| `No Balabit data in .../datasets/balabit` | The data is missing or one folder too deep/shallow: `experiment/datasets/balabit/users/user12/...` must exist (step 2). If it does, the notebook was opened from another folder: start Jupyter in `experiment/`, or set `EARL_HOME=/path/to/experiment`. |
| `pip could not install ...` | The kernel is the system Python, where Ubuntu blocks pip. Choose the **.venv (EARL)** kernel (section 4). |
| `No module named numba` or numba fails to install | Run step 3 again; on Python 3.14 numba must be 0.63 or newer. |
| `No such file or directory: .venv/bin/jupyter` | The terminal is not in `experiment/`: `cd ~/experiment` first. |
| `ValueError: Settings do not fit the data` | The message lists what to change in the Settings cell (section 5, limits). |
| `No finished runs ...: run section 3 first` | Switch `"batch"` on, or check that `SETTINGS` is the same as when the runs were made. |
| Started from the terminal and nothing appears | Normal. Watch `tail -f experiment_earl/runs/notebook_progress.log` or `bash status.sh`. |
| My settings change was ignored | The notebook was not saved before the terminal run. Save (`Ctrl+S`), stop and start again. |
| A batch run shows `failed` | The error is printed and saved in `runs/batch_log.csv`; the batch goes on with the next run. |
| Results land in a new `runs/<hash>/` folder | A value in `SETTINGS` differs from before. Put it back to reuse the old folder. |
| Kernel dies on a very large batch | Out of memory. Run fewer sensitivities at a time; finished runs are kept. |
