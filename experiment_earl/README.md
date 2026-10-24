# How to run the EARL experiment

This folder tests whether mouse-movement shapes from legitimate users can be told apart from impostors, using the Balabit dataset. This guide covers setup, the ways to run it, exporting the shapes as images, the find-the-sensitivity and find-the-sessions experiments, batch runs, picking the best setting, cohort scoring, the new-seed check, and where the results go. Every setting is explained in [CONFIG.md](CONFIG.md); how each script works (algorithm, formulas, and why) is in [docs/](docs/README.md); **how to read every figure** is in [READING_FIGURES.md](READING_FIGURES.md).

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
2. **Run** the notebook or the single trial (section 3).
3. **Open the results** in `experiment_earl/runs/<hash>/<L>_<I>_<sensitivity>_<sessions>/` (section 4). The script prints the folder.

Each distinct config gets its own run folder, so changing a setting never overwrites an older result. Running again with the same config reuses its folder.

## 3. What to run

### A. Notebook: sessions 1 → N (start here)

Tests `n_legitimate` legitimate users against `n_impostor` impostor users, with 1, 2, ... up to `sessions_per_user` sessions per user. **One RNG draw from `seed` fixes the legitimate users, the impostors and each user's session order for the whole run**; nothing is redrawn between steps or figures. Each step keeps the sessions of the step before and adds one. It makes a bar graph (impostors matched per session step), one bar graph per legitimate user, and a heatmap (sessions × legitimate users).

```bash
.venv/bin/python experiment_earl/src/07_run_notebook.py
```

This executes `notebooks/session_progression.ipynb` and saves the executed copy, with all tables and plots, in the run folder. You can also open the notebook in VS Code or Jupyter, pick the `.venv` kernel and run all cells; its CSVs and figures go to the same run folder, but the executed copy stays in `notebooks/` (clear its outputs before committing).

### B. Single trial, step by step (file-based)

One draw of `n_legitimate` + `n_impostor` users with `sessions_per_user` sessions each, with every intermediate file saved. Run the steps in order; each uses the files of the one before.

```bash
.venv/bin/python experiment_earl/src/01_sample_users.py      # pick users        -> temp/manifest.json
.venv/bin/python experiment_earl/src/02_sample_sessions.py   # pick sessions     -> temp/<class>/<user>/
.venv/bin/python experiment_earl/src/03_chunk_shapes.py      # cut into chunks   -> shapes/<class>/<user>/*.npz
.venv/bin/python experiment_earl/src/04_match_shapes.py      # compare chunks    -> results/trial_0.json
.venv/bin/python experiment_earl/src/05_sensitivity.py       # sensitivity       -> results/summary.csv
```

Step 04 also scores each legitimate user's own **held-out** sessions (the ones not drawn) against their profile, as a sanity check: they should match better than the impostors do. That is up to about 250 sessions per user.

### C. Export the shapes (lines) as images

Every chunk that step 03 cut out is one shape: a continuous mouse line between two pauses or clicks. Step 03 saves them as data (`.npz`); `06_plot_shapes.py` draws each one as a PNG, in a folder per user and session.

It needs the shapes of step 03, so run steps 01–03 first (once per config), then export:

```bash
.venv/bin/python experiment_earl/src/01_sample_users.py
.venv/bin/python experiment_earl/src/02_sample_sessions.py
.venv/bin/python experiment_earl/src/03_chunk_shapes.py      # saves the shapes as .npz

.venv/bin/python experiment_earl/src/06_plot_shapes.py       # draws every shape as a PNG
```

Useful options:

```bash
.venv/bin/python experiment_earl/src/06_plot_shapes.py --user user21              # one user only
.venv/bin/python experiment_earl/src/06_plot_shapes.py --user user21 --user user9 # several users
.venv/bin/python experiment_earl/src/06_plot_shapes.py --limit 50                 # at most 50 shapes per session
.venv/bin/python experiment_earl/src/06_plot_shapes.py --no-overview              # skip the overview grid
.venv/bin/python experiment_earl/src/06_plot_shapes.py --run 1a2b3c/1_9_0.04_10   # shapes of an older run
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

### D. Matched shapes behind the per-user bar graphs

Shows which impostor strokes matched which strokes of each legitimate user in the notebook (A): the same draw, users and sessions, one figure per legitimate user and session step. Each panel is one matched pair after normalization (what DTW compares): the impostor stroke (red dashed) on the user's stroke it matched (blue), with both session ids, chunk numbers and the DTW cost per point. The figure title repeats the bar graph's verdict per impostor (strokes matched, sessions at or above `match_shape_ratio`, matched or not). Run the notebook first so the run folder exists.

```bash
.venv/bin/python experiment_earl/src/08_plot_matches.py --run oct12_test2_d4015c                  # all users and steps, ~2 minutes
.venv/bin/python experiment_earl/src/08_plot_matches.py --run oct12_test2_d4015c --user user9 --sessions 2
.venv/bin/python experiment_earl/src/08_plot_matches.py --max 60                                   # more pairs per figure
```

Outputs, inside the run folder: `figures/matches/<user>_sessions<k>.png` (at most `--max` pairs, random sample) and `results/matches.csv` (every matched stroke of the drawn users and steps).

### E. Genuine check: own unused sessions against their own profile

The notebook (A) only asks whether impostors get through. This asks the opposite: does a legitimate user's own new session match their own profile? Same draw, same profiles (first 1, 2, ... `sessions_per_user` sessions) and the same `match_shape_ratio` rule. Each legitimate user's next `--held-out` sessions after the first `sessions_per_user` (default 2; never part of the profile at any step) are tested, next to the impostors' sessions against the same profile.

```bash
.venv/bin/python experiment_earl/src/09_genuine_check.py --run oct12_test3_d05fb2       # seconds once the DTW cache is warm
.venv/bin/python experiment_earl/src/09_genuine_check.py --held-out 5                    # more own sessions per user
```

Outputs, inside the run folder: `results/genuine_check.csv` (every tested session: share of strokes matched, passed or not), `results/genuine_check_summary.csv` and `figures/genuine_check.png` (one panel per legitimate user: own sessions blue, impostors red, label = sessions passed / tested).

### Working with an older run

Every script takes `--run <run folder>` (its path under `runs/`). It then uses that folder and the settings saved in it, whatever `config.yaml` says now:

```bash
.venv/bin/python experiment_earl/src/06_plot_shapes.py --run 1a2b3c/1_9_0.04_10 --user user12
.venv/bin/python experiment_earl/src/07_run_notebook.py --run 1a2b3c/1_9_0.02_10
```

Run folders are `<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>`: the hash covers every other setting (seed, chunking, matching, ...), so runs that differ only in those four sit side by side under one hash. Runs made before 2026-10-15 are flat `<run_name>_<hash>` folders and still open with `--run`. Runs made before 2026-10-08 used training files only; runs before 2026-10-14 read the separate `training_files`/`test_files` folders.

### Batch: many notebook runs at once

[batch.yaml](batch.yaml) lists a `seed`, the `splits` (`[n_legitimate, n_impostor]` pairs), the `sensitivities` and the `sessions` (sessions per user) to try. `11_batch.py` runs the notebook once for every combination, setting those values in `config.yaml` for each run and restoring it at the end; every other setting comes from `config.yaml` as it is. All the runs land side by side in one hash folder, `runs/<hash>/`, and the batch then calls F (`10_plot_accuracy.py`) on that folder and writes a summary.

```bash
.venv/bin/python experiment_earl/src/11_batch.py --dry-run     # list the runs and which are done, run nothing
.venv/bin/python experiment_earl/src/11_batch.py               # run them all, then plot (F)
.venv/bin/python experiment_earl/src/11_batch.py --only 0.03   # one sensitivity only (quick test)
.venv/bin/python experiment_earl/src/11_batch.py --no-plot     # skip F at the end
```

- **Resumable:** a run whose folder already has `results/session_progression.csv` is skipped, so rerunning the same command continues where it stopped and retries failed runs.
- **If it is killed**, `config.yaml.batch-backup` stays behind and the next start refuses to run. Check `config.yaml`, copy the backup over it if needed, delete the backup, then start again.
- **Outputs:** the run folders, `runs/batch_log.csv` (status and seconds per run), and in the hash folder F's files plus `summary/summary.csv` and `summary/README.md` (a table of every run with links to its plots).

### F. Sessions through per user across the runs of one hash folder

Runs that differ only in `n_legitimate`, `n_impostor`, `sensitivity` and `sessions_per_user` share one `runs/<hash>/` folder. This script scores every run in it and, per sensitivity, draws one figure with two line graphs: **legitimate users** (own last `sessions_per_user` sessions, never in a profile, against their own profile) and **impostor users** (their first `sessions_per_user` sessions, as in the notebook, against the legitimate profile that passes most of them). y = sessions that go through (≥ `match_shape_ratio` of strokes match), the notebook's fixed counts; one line per `sessions_per_user`; filled marker = the user goes through (≥ `match_session_ratio` of sessions).

```bash
.venv/bin/python experiment_earl/src/10_plot_accuracy.py            # the hash folder config.yaml selects
.venv/bin/python experiment_earl/src/10_plot_accuracy.py efdc92     # a specific hash folder
```

Outputs, in the hash folder: `runs/<hash>/accuracy.csv` (one row per run and user: sessions passed / tested, matched strokes, strokes, through, best profile) and `runs/<hash>/accuracy_<L>_<I>_sensitivity_<value>.png` (one per split and sensitivity). It is resumable: each finished sensitivity is saved in `runs/<hash>/accuracy_parts/` and reused on a rerun, so a killed run loses at most the sensitivity in progress. Delete `accuracy_parts/` to rescore everything (for example after changing the scoring code).

### G. The best sensitivity and sessions per split

After F, this reads `runs/<hash>/accuracy.csv` and scores every (split, sensitivity, sessions) cell twice, both as (legitimate accepted + impostors rejected) / 2 with 0.5 = chance: **user accuracy** counts users through (the group's 2026-10-14 rule) and ranks; **session accuracy** counts sessions and breaks ties (then fewer sessions, then lower sensitivity). Per split it keeps the best cell.

```bash
.venv/bin/python experiment_earl/src/12_pick_best.py            # the hash folder config.yaml selects
.venv/bin/python experiment_earl/src/12_pick_best.py 251ea4     # a specific hash folder
```

Outputs, in `runs/<hash>/best/` (rewritten each time): `best.csv` (one row per split, both accuracies, `beats_chance` = user accuracy above 0.5), `scores.csv` (every cell), `best_rows.csv` (the `accuracy.csv` rows of the chosen cells), `best_heatmaps.png` (sensitivity × sessions per split, colour = user accuracy, chosen cell boxed) and a copy of F's figure for each chosen split and sensitivity.

### H. Cohort scoring: does a session look more like its user than like other people?

Instead of 10's yes/no stroke match, this scores every session continuously: **raw** = how close its strokes are to the claimed user's library, **cohort** = for each stroke, the share of other people whose library is farther away than the claimed user's (0.5 = no evidence). Every library holds the same number of strokes (sessions × 40), because bigger libraries are closer to everything. It reports the EER and the best user accuracy per split next to G's best.

```bash
.venv/bin/python experiment_earl/src/13_cohort_score.py 251ea4                     # sessions 2–10 (minutes)
.venv/bin/python experiment_earl/src/13_cohort_score.py 251ea4 --max-sessions 30   # the whole batch range (much slower)
```

Outputs, in `runs/<hash>/cohort/`: `sessions.csv` (every claim with both scores), `cells.csv` (per split, sessions and method: EER, best threshold, users through, user and session accuracy), `best.csv` (best per split next to G's) and `cohort.png`.

### I. New-seed check: do the chosen settings hold?

G and H pick their best setting on the same runs they score. This takes each method's choice on the hash folder's seed (G: sensitivity + sessions; H: sessions + threshold, raw and cohort) and applies it unchanged to new seeds (new user order and sessions). Run F and G first.

```bash
.venv/bin/python experiment_earl/src/14_seed_check.py 251ea4                          # test seeds = seed + 1 ... + 3
.venv/bin/python experiment_earl/src/14_seed_check.py 251ea4 --test-seeds 11 22 33 44
```

Outputs, in `runs/<hash>/seed_check/`: `results.csv` (per split, method and seed: setting, users through, accuracies, EER), `summary.csv` (training value vs test mean / min / max) and `seed_check.png`.

### J. Draw what cohort scoring does

After H, this draws one genuine, one typical impostor and the top impostor claim for a user: each stroke next to its nearest stroke in the claimed user's library and in every other person's (red = closer than the claimed user's, against the claim; grey = farther, for it), plus every claim's score per split with the chosen threshold.

```bash
.venv/bin/python experiment_earl/src/15_plot_cohort.py 251ea4
.venv/bin/python experiment_earl/src/15_plot_cohort.py 251ea4 --user user9 --sessions 2 --strokes 8
```

Outputs, in `runs/<hash>/cohort/plots/`: `claim_<user>_{genuine,impostor_typical,impostor_top}.png` and `scores_per_split.png`.

### K. Sensitivity sweep: one confusion matrix per setting

For the fixed `splits` of `config.yaml` (only the users are drawn from `seed`), every library size 1 … `sweep_sessions_max` and every sensitivity of `sweep_sensitivity`, 16 accepts or rejects each test session (a legitimate user's last `sweep_test_sessions` against their own library, an impostor's first `sweep_test_sessions` against each legitimate library as a separate attempt) and counts TP / FP / FN / TN with positive = impostor. Each setting is counted from scratch; nothing is appended across iterations. 17 draws the result.

```bash
.venv/bin/python experiment_earl/src/16_sweep_sensitivity.py
.venv/bin/python experiment_earl/src/17_plot_sweep.py
```

Outputs, in `runs/<hash>/sweep/`: `confusion.csv` (one row per split, library size and sensitivity, with session- and user-level counts and the users drawn), `parts/` (one CSV per finished split, reused on a rerun; delete it after a code change), `config.yaml`, and from 17 `accuracy_vs_sensitivity.png`, `accuracy_heatmap.png`, `far_frr.png`, `confusion_matrices.png`. No best setting is picked.

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
│   ├── matches/<user>_sessions<k>.png   matched impostor strokes on the user's strokes  (D)
│   └── genuine_check.png                own unused sessions vs impostors, per profile   (E)
├── results/
│   ├── session_progression.csv          one row per session step                        (A)
│   ├── session_progression_steps.csv    every step, every impostor                      (A)
│   ├── session_progression_heatmap.csv  the heatmap's numbers                           (A)
│   ├── session_progression_users.csv    impostors matched per legitimate user and step  (A)
│   ├── trial_0.json                     per-impostor and held-out match ratios          (B)
│   ├── summary.csv                      sensitivity of the single trial                 (B)
├── results/matches.csv    every matched stroke behind the per-user bar graphs      (D)
├── results/genuine_check{,_summary}.csv  own unused sessions vs impostors     (E)
├── shapes/              chunks (.npz) and chunk PNGs                                (B, C)
└── temp/                drawn sessions and manifest.json                           (B)
```

Scripts that compare the runs of one hash folder write next to the run folders, not inside them:

```
experiment_earl/runs/
├── batch_log.csv                         status and seconds of every batch run        (batch)
└── <hash>/
    ├── <L>_<I>_<sensitivity>_<sessions>/ one folder per run (above)
    ├── summary/{summary.csv,README.md}   one row per run, with links to the plots     (batch)
    ├── accuracy.csv                      every run and user: sessions passed / tested  (F)
    ├── accuracy_parts/                   one finished sensitivity per file (resume)    (F)
    ├── accuracy_<L>_<I>_sensitivity_<v>.png  sessions through per user                (F)
    ├── best/                             best sensitivity + sessions per split         (G)
    │   ├── best.csv, scores.csv, best_rows.csv
    │   ├── best_heatmaps.png             sensitivity × sessions per split, best boxed
    │   └── accuracy_<L>_<I>_sensitivity_<v>.png   copies of F's chosen figures
    ├── cohort/                           cohort scoring                                (H)
    │   ├── sessions.csv, cells.csv, best.csv
    │   ├── cohort.png                    EER per split; best user accuracy vs G
    │   └── plots/                        claim_<user>_*.png, scores_per_split.png     (J)
    ├── seed_check/                       chosen settings on new seeds                  (I)
    │   ├── results.csv, summary.csv
    │   └── seed_check.png
    └── sweep/                            sensitivity × library size per split          (K)
        ├── confusion.csv, best.csv, splits.csv, config.yaml
        └── accuracy_vs_sensitivity.png, accuracy_heatmap.png, far_frr.png, confusion_best.png
```

**How to read every figure** (axes, colours, what good and bad look like, what we saw): [READING_FIGURES.md](READING_FIGURES.md). The short version:

- **Impostors matched**: how many impostor users looked like a legitimate user. Lower is better.
- **Sensitivity** (called *threshold* before 2026-10-14) = impostors matched / impostor users, from 0 to 1. 0 is best: no impostor passed.
- **User accuracy** (G, H, I): (legitimate users accepted / legitimate users + impostors kept out / impostors) / 2. 1 = perfect, **0.5 = chance**.
- **EER** (H, I): the error rate where genuine sessions rejected equal impostor sessions accepted. 0 = perfect, **0.5 = chance**.
- **Cohort score** (H, J): per stroke, the share of other people whose library is farther from it than the claimed user's; a session's score is the mean. **0.5 = no evidence**.
- G and H choose their best setting on the same sessions they score, so their values are optimistic; I tests the choices on new seeds.

The whole `runs/` folder is git-ignored: results stay on your computer. Copy a run folder to share it.

## 5. How long it takes

For the scripts (01–07), the first run of a new chunking or matching setting is the slowest, because every shape comparison (DTW) is computed once and then cached in `experiment_earl/cache/` for all later runs. The notebook keeps its own cache only while it runs, so every notebook run takes about the same time.

| What | Typical time |
|---|---|
| Notebook, 6 + 2 users, 1–5 sessions | about 1–2 minutes |
| Matched shapes (D), 6 users × 5 steps | about 2 minutes |
| Single trial 01–05 | a few minutes (step 04 also scores the held-out sessions) |
| Shape PNGs (C) for 10 users × 5 sessions | about 25 minutes (about 44,000 images) |
| Batch, one notebook run | 6 s (2 sessions) to 44 s (30 sessions); `251ea4` (6,750 runs) took about 40 hours |
| Sessions through (F), first time on `251ea4` | about 2 hours; a rerun with every part saved takes seconds, plus about 4 minutes to draw 450 figures |
| Best setting (G) | seconds |
| Cohort scoring (H), sessions 2–10 | about 3 minutes the first time, about 30 seconds with a warm cache |
| New-seed check (I), 3 new seeds | about 10 minutes |
| Cohort plots (J) | about a minute |
| Sensitivity sweep (K), 4 splits × 40 × 100 | about 3 minutes the first time, about 12 seconds with a warm cache; figures a few seconds |

More sessions per user means more shapes to compare, so runs beyond 5 sessions take noticeably longer.

## 6. Common problems

| Message | Fix |
|---|---|
| `... users do not fit in the 10 Balabit users` | Lower `n_legitimate` or `n_impostor`: they must add up to 10 or less. |
| `sessions_per_user = N but some user has only M sessions` | Lower `sessions_per_user` to M or less (114). |
| `No run '...' under .../runs` | The `--run` name is wrong; the message lists the existing runs. |
| `ModuleNotFoundError: numba` (or `nbformat`) | Use `.venv/bin/python`, or redo the setup in section 1. |
| `'RcParams' object has no attribute '_get'` | Run `.venv/bin/pip install "matplotlib-inline<0.2"`. |
| `Run ... has no shapes yet` from `06_plot_shapes.py` | That run only has notebook results. Run steps 01–03 with the same `--run` (the message prints the commands), then export. |
| `Need N sessions per user (sessions_per_user + 2 tested)` | Lower `sessions_per_user` (at most 112). |
| `No shapes for userX in run ...` | That user was not drawn in this run's single trial; the message lists the users that have shapes. |
| `config.yaml.batch-backup exists: an earlier batch did not finish cleanly` | A batch was killed. Check `config.yaml`, copy the backup over it if needed, delete the backup, then rerun. |
| `Killed` while running F on a large hash folder | Out of memory (fixed 2026-10-19: F now keeps one sensitivity at a time). Rerun; finished sensitivities in `accuracy_parts/` are reused. |
| `No .../accuracy.csv: run 10_plot_accuracy.py <hash> first` | Run F before G. |
| `No .../cohort/sessions.csv: run 13_cohort_score.py <hash> first` | Run H before J. |
| `Needs run folders and .../best/best.csv: run 10 and 12 on <hash> first` | Run F and G before I. |
| `Pools too small for N sessions` | Lower `--max-sessions` (H, I); every user needs about 3 × that many sessions. |
