# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An undergraduate thesis (4-member group): **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication."** It is half writing, half experiments:

- `paper/` — the written research: literature, survey, chapter drafts, adviser log, and writing tools.
- `experiment_earl/` — YAML config, numbered scripts in `src/`, a notebook, raw datasets (`datasets/`), and generated results/figures. This is the **only** experiments folder. Two earlier code bases are gone from the working tree but live in git history: the old `experiments/` folder (first-movement capture, stroke extraction; removed in `d10f50c`, e.g. `f36850c`) and Earl's 1-second-chunk prototype (`experiment_earl/scripts/` hull profiles + One-Class SVM benchmark, `configs/ocsvm.toml`, `temp/` reference CSVs; last present in `ab09dad`).

The originally proposed method (5 stages: short-stroke segmentation → closed-form geometry → convex hull bounding → Discrete Fréchet distance → dynamic trust threshold) is **not implemented**. What exists now is the EARL shape-matching experiment (see `EARL_EXECUTION_PLAN.md` and the section below): pause-based chunks, resampled and compared with banded DTW against legitimate-user libraries. `EARL_IDEA.md` is Earl's numbered idea list, which `EARL_EXECUTION_PLAN.md` turns into steps; `image.png` is the whiteboard sketch behind the session-progression notebook (legitimate set L, impostor set I, sessions × users heatmap on a 0–1 scale).

`README.md` still describes the deleted `experiments/` layout and is out of date; trust this file and the code.

## Commands

Run from the repo root. There is no build, test suite, or linter. Use the git-ignored `.venv`: it was made with `python3 -m venv --system-site-packages .venv` and adds numba, nbformat, nbconvert and ipykernel on top of the system packages. With the system matplotlib 3.6, `matplotlib-inline` must stay `<0.2` or notebook plots fail with `'RcParams' object has no attribute '_get'`.

```bash
pip install -r requirements.txt     # pandas, pyarrow, shapely, matplotlib, jupyter, ipykernel, scikit-learn, numba, pyyaml

# EARL shape matching (see section below)
# All simulations now run in experiment_earl/notebooks/earl_simulation.ipynb (.venv kernel, edit Settings, Run All;
# adviser 2026-10-26). The src/ scripts below still exist until the notebook replaces them.
.venv/bin/python experiment_earl/src/01_sample_users.py   # then 02 ... 05 (one trial)
.venv/bin/python experiment_earl/src/06_plot_shapes.py     # PNG per chunk under shapes/
.venv/bin/python experiment_earl/src/10_plot_accuracy.py    # sessions through per user, one row per run -> runs/<hash>/accuracy.csv
.venv/bin/python experiment_earl/src/12_pick_best.py        # best sensitivity + sessions per split -> runs/<hash>/best/
.venv/bin/python experiment_earl/src/13_sweep_sensitivity.py # fixed splits x library size x sensitivity, confusion matrix per setting -> runs/<hash>/sweep/
.venv/bin/python experiment_earl/src/14_plot_sweep.py       # draw 13's sweep (accuracy, heatmap, FAR/FRR, confusion matrices)
.venv/bin/python experiment_earl/src/15_best_setting.py     # best sensitivity + sessions per user, picked on half the tests, checked on the other -> runs/<hash>/sweep/best/
cd experiment_earl/notebooks && ../../.venv/bin/jupyter nbconvert --to notebook --execute --inplace session_progression.ipynb

# Paper tools
python paper/tools/audit_writing.py <draft.md> [-v] [--json]   # AI-detector cadence audit
python paper/references/example-rrl-fetch.py [--dry-run] [--queries ...]
```

### Conventions to match

- Each script: shebang + one-line module docstring, `argparse` with `description=__doc__`, `ROOT = Path(__file__).resolve().parents[1]` (resolves to `experiment_earl/`), `main()` that prints a short summary (counts + output path).
- Experiment settings go in `config.yaml` with explanatory comments, not as new CLI flags.
- Small, plain functions; type hints on signatures; sparse comments.

## Data facts that are easy to get wrong

Datasets are under `experiment_earl/datasets/` and are committed to git (~1,900 session files).

- **Balabit** session files have **no extension** (`session_0032069206`); glob with `*`. Columns: `record timestamp, client timestamp, button, state, x, y`. Timestamps are **seconds** (floats). Balabit shipped `training_files` (65 sessions, genuine only) and `test_files` (1,611, mixed genuine/impostor; `public_labels.csv` labels 816 of them, `is_illegal = 1` for impostors). Since 2026-10-14 (adviser) both are **merged** with `git mv` into `datasets/balabit/users/<user>/` (114–253 sessions per user); the old folders no longer exist in git.
- **SapiMouse** (`datasets/sapimouse/`, 120 users, 245 files `session_<date>_{1min,3min}.csv`): columns `client timestamp, button, state, x, y`, timestamps in **milliseconds**. No script uses it currently.
- `state ∈ {Move, Drag, Pressed, Released}`. `y` grows downward (screen coordinates) — plots call `invert_yaxis()`.
- Balabit users: `user7, user9, user12, user15, user16, user20, user21, user23, user29, user35`.
- Some Balabit rows have **x = y = 65535** (logging glitches, not positions). Drop them before any spatial computation or they create ~60,000 px jumps.
- Balabit `record timestamp` has ~0.1 s resolution, so ~90% of rows tie with a neighbor; `client timestamp` is ~16 ms and steps backward in one session (sort stably, or use `np.maximum.accumulate`). Don't re-sort: pandas' default sort is unstable and reorders ties. Use file order or a stable sort.
- Sampling rate and screen size differ by user: user7/9/20 log every ~16 ms, the rest every ~110 ms; screens range from 1280×800 (user23) to 1920×1080 (user15/16). Per-point features and hull extents partly measure these rather than behavior. Resample/normalize before claiming user differences.
- **All of Balabit is used, raw** (adviser + group decision, 2026-10-08): a session belongs to the user whose folder it is in. `public_labels.csv` is **not** used (a label-based design was tried and dropped the same day). `00_config.session_pool(config, user, seed)` = every session in the user's merged folder, shuffled once with `Random(f"{seed}-{user}")` (since 2026-10-14; before, training sessions came first, then test sessions, so old runs are not reproducible with the new order). Pools are 114–253 sessions, so session counts can reach 114.
- Earl's old prototype example session (`user15/session_0003960194`) is a **test** session labelled impostor, not user15's genuine data. Don't build profiles from it.

## EARL shape-matching experiment (`experiment_earl/src/`, Balabit only)

Plan: `EARL_EXECUTION_PLAN.md`; every setting is explained in `experiment_earl/CONFIG.md`, `experiment_earl/README.md` is the user-facing run guide, `experiment_earl/READING_FIGURES.md` explains how to read every figure (example images in `experiment_earl/docs/figures/`, since `runs/` is git-ignored), and `experiment_earl/docs/NN_*.md` explain each script's algorithm, formulas and reasons (keep both in sync when commands, outputs or algorithms change). Run with `.venv/bin/python experiment_earl/src/NN_*.py` (numba lives in the git-ignored `.venv`): 01 → 05 is one file-based trial (`temp/` → `shapes/` → `results/trial_0.json`, `summary.csv`), 06 draws the chunks saved by 03, 07 executes the notebook (no `.ipynb` copy is saved), 08 and 09 reproduce the notebook's draw (matched shapes, genuine check), 10 compares the runs of one hash folder; settings in `experiment_earl/config.yaml`.

**Simulation notebook (`experiment_earl/notebooks/earl_simulation.ipynb`, adviser 2026-10-26: replace the scripts, run every simulation in a notebook):** self-contained, no imports from `src/`; one Settings cell (`SETTINGS` = config.yaml's non-run, non-sweep keys, so its `runs/<hash>/` matches config.yaml's; `BATCH`, `SWEEP`, `SINGLE_RUN`, `SECTIONS` switches). Sections: batch (per run `results/accuracy.csv` + `session_progression*.csv`, runs ordered by sensitivity so DTW pairs are reused in one kernel), accuracy + summary (10/11), best per split (12), sweep (13), best setting per user (15), optional matched pairs (08) and genuine check (09). CSV only, no figures (the group writes the figure code). Everything it prints is also appended to `runs/notebook_progress.log` (setup cell wraps `sys.stdout`), so a background run (`nohup .venv/bin/jupyter execute ... &` from the Jupyter terminal, adviser 2026-10-26) can be followed with `tail -f`; `progress()` lines are timestamped and report each run's / sweep split's inner steps (users drawn, session step, impostor, sessions tested every 10) plus an ETA, and `notebooks/status.sh` prints running/PID/CPU, any error and the last progress lines (helper is named `progress`, since section 6 has a local `step`). Generated 2026-10-26 and checked on a small config (seed 1): every CSV equal to the scripts' and the old notebook's. Auto-restart/resume after a server restart is deliberately not built yet; `SKIP_FINISHED_RUNS` only skips runs whose `results/accuracy.csv` exists.

**Runs:** nothing writes into fixed folders. `00_config.open_run()` maps the current config to `experiment_earl/runs/<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>/` (hash = every other setting; `run_name` was dropped 2026-10-15, older runs are flat `<run_name>_<hash>` folders), creating it with a `config.yaml` snapshot and `run.json` on first use. `results/`, `figures/`, `shapes/` and `temp/` live inside it. Any config change → new folder, so earlier results are never overwritten. Every script takes `--run <hash>/<name>` (the notebook reads `EARL_RUN`) to reuse an old run with its own settings. The whole `runs/` folder and the shared DTW cache (`experiment_earl/cache/`) are git-ignored: results stay on disk for reference but are not committed.

- **Sensitivity sweep (`13_sweep_sensitivity.py`, `14_plot_sweep.py`, merged 2026-10-24):** the `splits`, `sweep_sensitivity`, `sweep_sessions_max` and `sweep_test_sessions` keys are in `00_config.SWEEP_KEYS` and left out of the run hash, so the sweep writes into `runs/<hash>/sweep/`. Each split is a fresh `Random(seed)` draw (`08.draw_users`). Impostor sessions are tested against each legitimate library as a separate attempt (not accepted on any one library); sessions with `is_illegal = 1` are dropped via `labels_file`; session- and user-level counts; 13 itself picks no best setting; 15 picks one per user and per split on the even test sessions and reports it on the odd ones. Own DTW cache `cache/distances.pkl`; finished splits are reused from `sweep/parts/`. `Sensitivity Sweep Process and Results.md` was produced by Earl's earlier version (any-library rule, illegal sessions kept, best pick), so its numbers need a rerun.
- Scripts are numbered, so modules load with `import_module("00_config")`. `08_plot_matches.py` and `09_genuine_check.py` reuse `dataset_session` and `matched_chunks` from `04_match_shapes.py`; pair results are cached in `experiment_earl/cache/pairs.pkl` (shared by all runs).
- Balabit has only 10 users, so `n_legitimate + n_impostor <= 10` (plan's 5/10/15/20 impostors are impossible). Step 02 clears only `temp/legitimate` and `temp/impostor`.
- **Sensitivity = former threshold** (adviser, 2026-10-14): every "threshold" was renamed, so `05_sensitivity.py` and the notebook report `sensitivity` = impostors matched / impostors. The DTW tolerance key itself is `sensitivity` too (renamed from `dtw_tolerance` 2026-10-14; `00.load_config` maps the old name in old run snapshots). **DTW only**: the One-Class SVM and every hull/anomaly script (old 09–13) were removed the same day; they are in git history (last in `edcfcf5`).
- **Known result:** chunk matching does not discriminate. At `sensitivity` (formerly `dtw_tolerance`) 0.15 about 99% of all chunks match; at 0.01–0.06 and with longer chunks (gap 1–3 s, min length 100–300 px) a user's own held-out sessions never match more than impostors do (AUC 0.27–0.50). The current 0.02 is only the value that keeps the heatmap non-trivial. Treat bar/heatmap numbers as a baseline, not evidence of unique shapes.
- **Seed check (2026-10-19, on `251ea4`; script 14 and the cohort scripts 13 and 15 were removed 2026-10-26):** settings chosen on seed 927 and applied unchanged to seeds 928–930 fall to chance: mean user accuracy 12's matching 0.63 → 0.44, 13 raw 0.70 → 0.50, 13 cohort 0.82 → 0.42 (test EER 0.44–0.46). Equal-size libraries matter (bigger profiles let more impostors through), but neither cohort scoring nor tuning makes stroke shape identify users.

### Matched shapes (`src/08_plot_matches.py`)

- Reproduces the notebook's single draw (`seed`; legitimate users in draw order, the same set as script 01's sorted draw) and, per legitimate user and session step, finds for every impostor stroke the first matching stroke in the user's first k sessions (`first_match`, same banded DTW search as `04.has_match`). Writes all matched pairs to `results/matches.csv` and prints the per-impostor verdict (the PNG figures were removed 2026-10-26); on `oct12_test2_d4015c` and `oct12_test2_e36855` all 30 agree with `session_progression_users.csv`. ~2 min for 6 users × 5 steps.
- Seen so far: matched pairs are mostly near-straight lines, which is why shapes match across users.

### Genuine check (`src/09_genuine_check.py`)

- Same draw and profiles as the notebook (`08.draw_users`); per legitimate user and step k, scores the user's next `--held-out` (default 2) sessions after the first `sessions_per_user` (never in the profile) and the impostors' first k sessions against the user's first-k-session library with `04.matched_chunks` (shared DTW cache) and the `match_shape_ratio` rule. Outputs `results/genuine_check{,_summary}.csv` (no figure since 2026-10-26).
- First result (`oct12_test3_d05fb2`, impostors user16 + user21): own sessions pass only for user9 and user20 (2/2 from 1–2 sessions, 35–57% of strokes matched) and user29 at 4–5 sessions (1/2); user12, user15, user35 never pass (11–21%). Own share beats the impostors' for 5 of 6 users, but user9/user20 are also the users that get through as impostors, so passing tracks a user's straight-stroke style more than identity. user15/user35 held-out sessions include short test files (44–61 strokes). This run predates the data merge.

### Sessions through across runs (`src/10_plot_accuracy.py`)

- Takes a hash folder (`runs/<hash>/`, default the current config's) and scores every run in it with its own snapshot, using the notebook's **fixed counts** (user request 2026-10-15; an earlier version plotted the share of strokes matched): y = sessions that go through (≥ `match_shape_ratio` of strokes match). Legitimate = the user's last `sessions_per_user` pool sessions (never in a profile) against their own library; impostor = their first `sessions_per_user` sessions against the legitimate library that passes most of them. A user is through at ≥ `match_session_ratio` of sessions. Output: `runs/<hash>/accuracy.csv` only (the per-sensitivity PNGs were removed 2026-10-26). Impostor counts equal the notebook's `sessions_matched` and "impostors matched" on all 11 runs of `efdc92`. ~10 s with a warm DTW cache.
- First result (`efdc92`, seed 945, user29 legitimate vs 9 impostors): at 0.02 almost nothing goes through (user29 1/10 at 10 sessions, impostors 0–5 of 90 sessions); at 0.04 user29 goes through from 4 sessions (3/4 … 10/10) but so do 4, 7, 9, 9 of 9 impostors at 4, 6, 8, 10 sessions; at 0.06 / 2 sessions user29 2/2 and 8 of 9 impostors. No sensitivity accepts the user while rejecting impostors.

### Notebook (`experiment_earl/notebooks/session_progression.ipynb`)

- Self-contained copy of the 00–05 logic (loader, chunking, numba DTW, per-profile matching): changes to `src/` do **not** reach it, and vice versa. Keep them in sync by hand.
- Experiment (all from `config.yaml`, nothing hardcoded): **one draw from `seed`** fixes `n_legitimate` legitimate + `n_impostor` impostor users and every user's session order for the whole run (user decision 2026-10-12); sessions per user 1 → `sessions_per_user` (nested: step k+1 reuses step k's sessions); the heatmap columns reuse the draw with its first 1…`n_legitimate` legitimate users (draw order, not sorted). 6 + 2 users, 1–5 sessions run in ~1–2 min.
- Outputs (inside the run folder): `results/session_progression{,_steps,_heatmap,_users}.csv`, `figures/session_progression.png` (bar: **impostors matched**, not the sensitivity, as requested), `figures/session_progression_users.png` (same count split into exactly `n_legitimate` panels, one per legitimate user of the draw, tallest bar red; `matched_by` in the steps CSV lists every profile an impostor matched) and `figures/session_progression_heatmap.png` (colour = sensitivity 0–1 in 0.1 steps, cells also show impostors matched).

## Thesis-writing workflow

- **Read `paper/references/adviser-log.md` first** before giving thesis direction; the newest entry (top) wins. Scope as of 2026-08-31: capture user mannerisms from **short** mouse signals/trajectories, not long sessions. "Short signal" and which mannerisms to prioritize are still open questions.
- When the user shares adviser feedback, add a dated entry to the **top** of the adviser log using the template in that file.
- Skills in `.agents/skills/` (mirrored at root `SKILL.md`): `mouse-biometrics-thesis` (domain + adviser log), `academic-writing` (tone, chapter templates), `humanize-academic-writing` (burstiness / anti-cliché rules). Follow them for chapter drafting, and run `paper/tools/audit_writing.py` on drafts.
- Citations are IEEE style. Only cite papers that exist in `paper/references/` (`rrl-candidate-papers.md`, `measurement-comparison-survey.md`, `new-candidates.md`) or that the user provides; never fabricate references.
- `paper/references/plan.md` logs completed task plans; append a new plan section when finishing a sizable paper task.
- `paper/references/annotated-bibliography.md` was **deleted** in commit `571a828`, but the skills and `example-rrl-fetch.py` still reference it (the fetcher warns and continues without filtering known papers). `paper/references/pipeline.md` is referenced but does not exist (a 2026-10-18 version was deleted at the user's request). Tell the user if a task depends on them; don't invent their contents.
- `example-rrl-fetch.py` resolves its bibliography and `new-candidates.md` relative to its own directory — keep it inside `paper/references/`.
- `temp.md` is a local scratch prompt (git-ignored), not project content.

## Git and CI

- Remote: `github.com/chrjym/thesis-mouse-biometrics`. Default branch `main`; feature work happens on branches (e.g. `chrjym1`).
- `.github/workflows/literature-checker.yml` runs every Monday 00:00 UTC (and on manual dispatch) and **pushes commits to `main`** from `github-actions[bot]` updating `paper/references/new-candidates.md`. Pull before pushing to `main`, and expect conflicts in that file. If you move `example-rrl-fetch.py` or `new-candidates.md`, update the workflow paths too.
- Commit locally after every completed change with a descriptive message; never push unless asked.
- Commit messages must contain **no names**: no `Co-Authored-By` trailer, no tool or person attribution (user instruction, 2026-10-08).
- Don't commit `__pycache__/`, `.venv/`/`venv/`, or notebook checkpoints (see root `.gitignore`).
