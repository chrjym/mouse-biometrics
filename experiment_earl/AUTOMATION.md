# How to run the automation (`11_batch.py`)

`src/11_batch.py` runs every simulation listed in `batch.yaml` with one command, then plots and summarizes the results. You never edit `config.yaml` by hand: the script sets it for each run and puts it back afterwards.

Run every command from the **repository root** (`thesis-mouse-biometrics/`). On Windows, replace `.venv/bin/python` with `.venv\Scripts\python`.

## At a glance

| | |
|---|---|
| **Input** | `experiment_earl/batch.yaml` (what to run) + `experiment_earl/config.yaml` (every other setting) |
| **Command** | `.venv/bin/python experiment_earl/src/11_batch.py` |
| **Output** | `experiment_earl/runs/<hash>/`: one folder per run, accuracy plots, `summary/` overview; `runs/batch_log.csv` |

---

## Step 1: Get the latest code

```bash
git pull --rebase
```

The `.venv` must exist (see section 1 of [README.md](README.md) for the one-time setup).

## Step 2: Set the input in `batch.yaml`

Open `experiment_earl/batch.yaml` and choose what to run:

```yaml
seed: 945
splits:                                        # [n_legitimate, n_impostor]
  - [1, 9]
  - [2, 8]
  - ...                                        # up to [9, 1]
sensitivities: [0.20, 0.40, 0.60, 0.80, 1.00]  # DTW tolerance, steps of 0.2
sessions: [2, 4, 6, 8, 10]                     # sessions_per_user
```

| Key | What it means | Rules |
|---|---|---|
| `seed` | Picks the users and each user's session order. Same seed = same users and sessions. | any whole number |
| `splits` | `[n_legitimate, n_impostor]` pairs: users whose strokes form the profiles, and other users tested against them. The default steps legitimate 1 → 9 while impostors go 9 → 1. | each pair adds up to at most 10 |
| `sensitivities` | DTW tolerance: a stroke matches when its mean distance per point is at most this. Lower = stricter. | list of numbers |
| `sessions` | Profile sessions per user (`sessions_per_user`) | list, each at most 114 |

The batch runs **every split with every sensitivity and every session count**: 9 × 5 × 5 = 225 runs with the values above (about 15–25 s each, so roughly 1–1.5 hours). Shorten the lists for a smaller batch, e.g. `splits: [[1, 9]]` gives 25 runs.

Every other setting (chunking, `dtw_band`, `match_shape_ratio`, `match_session_ratio`, data folder) comes from `config.yaml` as it is. Explained in [CONFIG.md](CONFIG.md).

> **Two members running the same plan:** keep `seed` and `config.yaml` identical, and give each member different `splits` (e.g. one takes 1–9 to 5–5, the other 6–4 to 9–1). All runs then land in the same `runs/<hash>/` folder and are plotted together.

## Step 3: Check the plan (dry run)

```bash
.venv/bin/python experiment_earl/src/11_batch.py --dry-run
```

Lists every run and whether it is done already. Runs nothing and changes nothing.

```
[1/225] efdc92/1_9_0.2_2 ... to run
[2/225] efdc92/1_9_0.2_4 ... to run
...
Dry run: 225 runs, 0 done, 225 to run.
```

The run name is `<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions>`.

## Step 4: Run the batch

```bash
.venv/bin/python experiment_earl/src/11_batch.py
```

What happens, in order:

1. **Back up** `config.yaml` (to `config.yaml.batch-backup`).
2. **For each run:**
   1. **Skip** it if its folder already has `results/session_progression.csv`.
   2. **Set** `seed`, the split (`n_legitimate`, `n_impostor`), `sensitivity` and `sessions_per_user` in `config.yaml`.
   3. **Simulate:** run `07_run_notebook.py` (pick users and sessions → cut strokes → DTW matching → decide which sessions and users pass).
   4. **Print** progress, e.g. `[7/225] efdc92/1_9_0.4_6 ... ok (0m 26s)`.
   5. **Log** one line to `runs/batch_log.csv`.
   6. If the run **fails**, note it and continue with the next.
3. **Restore** `config.yaml`, even after an error or Ctrl+C, and delete the backup.
4. **Summary:** runs ok, skipped and failed, and a `git add` command for the new run folders.
5. **Plot:** run `10_plot_accuracy.py` on the hash folder.
6. **Summarize:** write `summary/summary.csv` and `summary/README.md`.

Options:

| Option | Effect |
|---|---|
| `--dry-run` | list the runs only (step 3) |
| `--only 0.4` | run a single sensitivity (quick test) |
| `--no-plot` | skip the plotting and summary (steps 5–6) |
| `--plan <file>` | use another plan file instead of `batch.yaml` |
| `--timeout 3600` | seconds allowed per run (default 3600) |

**Stopping and resuming:** press Ctrl+C at any time. Run the same command again: finished runs are skipped, so it continues where it stopped. Failed runs are retried the same way.

## Step 5: Read the output

Everything is in `experiment_earl/runs/`:

```
runs/
├── batch_log.csv                       which runs finished or failed, and how long each took
└── <hash>/                             one folder per set of shared settings (e.g. efdc92)
    ├── summary/                        START HERE
    │   ├── README.md                   results table + links to every plot and run folder
    │   └── summary.csv                 one row per run
    ├── accuracy.csv                    every run x every user
    ├── accuracy_1_9_sensitivity_0.2.png  one plot per split and sensitivity
    ├── accuracy_1_9_sensitivity_0.4.png
    ├── ...
    └── 1_9_0.2_2/                      one folder per run
        ├── config.yaml                 exact settings of this run
        ├── run.json                    when it was created, git commit
        ├── results/                    session_progression*.csv
        ├── figures/                    bar graphs and heatmap
        └── notebooks/                  the executed notebook
```

### `summary/summary.csv` columns

| Column | Meaning |
|---|---|
| `split`, `n_legitimate`, `n_impostor` | the run's split (`1_9` = 1 legitimate vs 9 impostors) |
| `sensitivity`, `sessions` | the run's settings |
| `run` | run folder |
| `legit_passed` / `legit_tested` | legitimate user's own tested sessions that pass their profile (**higher is better**) |
| `legit_accepted` | legitimate users accepted (at least `match_session_ratio` of their sessions pass) |
| `impostor_passed` / `impostor_tested` | impostor sessions that pass the profile (**lower is better**) |
| `impostors_through` | impostors who get through |

### The plots (`accuracy_<legit>_<impostor>_sensitivity_<value>.png`)

One figure per split and sensitivity, so splits are never mixed.

- **Left panel, legitimate:** x = each legitimate user, y = their sessions that pass.
- **Right panel, impostor:** x = each impostor, y = their sessions that pass.
- **One line per session count**; a filled marker means the user as a whole goes through.

### `batch_log.csv` columns

`time`, `run`, `status` (`ok` / `failed`), `seconds`, `error` (last line of the error message).

**What a good result looks like:** a sensitivity and session count where the legitimate user is accepted and few impostors get through.

## Step 6: Share the results (optional)

`runs/` is git-ignored, so adding it needs `-f`. Agree first on who commits; `accuracy.csv`, the plots and `summary/` are rewritten by every batch.

```bash
git add -f experiment_earl/runs/<hash>/1_9_0.2_2 ...   # the command printed at the end of the batch
git commit -m "experiment: batch runs sensitivity 0.2-1.0"
git pull --rebase && git push
```

Never commit `config.yaml` changes made for a run; the batch always restores it.

## Troubleshooting

| Message | What to do |
|---|---|
| `config.yaml.batch-backup exists: an earlier batch did not finish cleanly` | The computer stopped mid-run. Compare `config.yaml` with the backup, restore if needed (`cp experiment_earl/config.yaml.batch-backup experiment_earl/config.yaml`), then delete the backup. |
| `config.yaml has no line '<key>: ...'` | A key in `config.yaml` was renamed or removed. Put it back as `<key>: <value>` at the start of a line. |
| A run shows `failed` | Read its `error` in `batch_log.csv`, fix the cause, run the batch again (only missing runs run). |
| `Plotting runs/<hash> failed` | The runs are kept. Rerun: `.venv/bin/python experiment_earl/src/10_plot_accuracy.py <hash>` |
| Runs land in a new hash folder | A setting other than the five in `batch.yaml` differs from before. Check `config.yaml` with `git diff`. |
