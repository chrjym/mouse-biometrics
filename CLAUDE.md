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
.venv/bin/python experiment_earl/src/01_sample_users.py   # then 02 ... 05 (one trial)
.venv/bin/python experiment_earl/src/06_sweep.py           # full sweep, resumable
.venv/bin/python experiment_earl/src/07_plot_shapes.py     # PNG per chunk under shapes/
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

- **Balabit** session files have **no extension** (`session_0032069206`); glob with `*`. Columns: `record timestamp, client timestamp, button, state, x, y`. Timestamps are **seconds** (floats). `training_files` (65 sessions) are genuine only; `test_files` (1,611) mix genuine and impostor; `public_labels.csv` labels only 816 of them (`is_illegal = 1` for impostors).
- **SapiMouse** (`datasets/sapimouse/`, 120 users, 245 files `session_<date>_{1min,3min}.csv`): columns `client timestamp, button, state, x, y`, timestamps in **milliseconds**. No script uses it currently.
- `state ∈ {Move, Drag, Pressed, Released}`. `y` grows downward (screen coordinates) — plots call `invert_yaxis()`.
- Balabit users: `user7, user9, user12, user15, user16, user20, user21, user23, user29, user35`.
- Some Balabit rows have **x = y = 65535** (logging glitches, not positions). Drop them before any spatial computation or they create ~60,000 px jumps.
- Balabit `record timestamp` has ~0.1 s resolution, so ~90% of rows tie with a neighbor; `client timestamp` is ~16 ms and steps backward in one session (sort stably, or use `np.maximum.accumulate`). Don't re-sort: pandas' default sort is unstable and reorders ties. Use file order or a stable sort.
- Sampling rate and screen size differ by user: user7/9/20 log every ~16 ms, the rest every ~110 ms; screens range from 1280×800 (user23) to 1920×1080 (user15/16). Per-point features and hull extents partly measure these rather than behavior. Resample/normalize before claiming user differences.
- Earl's old prototype example session (`user15/session_0003960194`) is a **test** session labelled impostor, not user15's genuine data. Don't build profiles from it.

## EARL shape-matching experiment (`experiment_earl/src/`, Balabit only)

Plan: `EARL_EXECUTION_PLAN.md`; every setting is explained in `experiment_earl/CONFIG.md`. Run with `.venv/bin/python experiment_earl/src/NN_*.py` (numba lives in the git-ignored `.venv`): 01 → 05 is one file-based trial (`temp/` → `shapes/` → `results/trial_0.json`, `summary.csv`), 06 is the sweep, 07 draws the chunks saved by 03, 08 executes the notebook; settings in `experiment_earl/config.yaml`.

**Runs:** nothing writes into fixed folders. `00_config.open_run()` maps the current config (all values except `run_name`, hashed) to `experiment_earl/runs/<name>_<hash>/`, creating it with a `config.yaml` snapshot and `run.json` on first use. `results/`, `figures/`, `shapes/`, `temp/` and `notebooks/` (executed notebook) live inside it. Any config change → new folder, so earlier results are never overwritten. Every script takes `--run <folder>` (the notebook reads `EARL_RUN`) to reuse an old run with its own settings. The whole `runs/` folder and the shared DTW cache (`experiment_earl/cache/`) are git-ignored: results stay on disk for reference but are not committed.

- Scripts are numbered, so modules load with `import_module("00_config")`. `06_sweep.py` reuses `dataset_session` and `matched_chunks` from `04_match_shapes.py`; pair results are cached in `experiment_earl/cache/pairs.pkl` (shared by all runs).
- Balabit has only 10 users, so `n_legitimate + n_impostor <= 10` (plan's 5/10/15/20 impostors are impossible). Step 02 clears only `temp/legitimate` and `temp/impostor`.
- **Known result:** chunk matching does not discriminate. At `dtw_tolerance` 0.15 about 99% of all chunks match; at 0.01–0.06 and with longer chunks (gap 1–3 s, min length 100–300 px) a user's own held-out sessions never match more than impostors do (AUC 0.27–0.50). The current 0.02 is only the value that keeps the heatmap non-trivial. Treat bar/heatmap numbers as a baseline, not evidence of unique shapes.

### Full sweep (`src/06_sweep.py`)

- Every (sessions 1..`sweep_sessions_max`) × (legitimate users) × (impostor users) cell with L + I ≤ 10, over `n_trials` draws. Per draw the 10 users are shuffled once: legitimate = front of the list, impostors = back, sessions = prefix of a shuffled order, so cells are nested and comparable. It scores every (impostor, legitimate) pair once (`runs/<run>/results/sweep/pairs.csv`) and builds all cells from that.
- Resumable: seeds already in `pairs.csv` are skipped, so a rerun only redraws the figures. First run ~30 min (fills the DTW cache).
- Outputs (inside the run folder): `results/sweep/{summary,saturation}.csv`, `figures/sweep_{heatmaps,lines}.png`. `saturation.csv` gives, per curve, where changes drop below `sweep_delta` and the biggest jump.
- Result (tol 0.02, 20 draws): sessions per user drive the threshold (1→2 sessions jumps ~0.2, flat from ~4); legitimate users add a slow rise (0.16 → 0.27 over 1 → 9); impostor count barely matters (the threshold is already a share).

### Notebook (`experiment_earl/notebooks/session_progression.ipynb`)

- Self-contained copy of the 00–05 logic (loader, chunking, numba DTW, per-profile matching): changes to `src/` do **not** reach it, and vice versa. Keep them in sync by hand.
- Experiment (all from `config.yaml`, nothing hardcoded): `n_legitimate` legitimate + `n_impostor` impostor users, sessions per user 1 → `sessions_per_user` (nested: step k+1 reuses step k's sessions), `n_trials` seeded draws; the heatmap columns reuse each draw with the first 1…`n_legitimate` legitimate users (draw order, not sorted). Default config: 3 + 2 users, 1–3 sessions, 20 draws; runs in ~5 min.
- Outputs (inside the run folder): `results/session_progression{,_trials,_heatmap}.csv`, `figures/session_progression.png` (bar: mean **impostors matched**, not the threshold, as requested) and `figures/session_progression_heatmap.png` (colour = threshold 0–1 in 0.1 steps, cells also show impostors matched).

## Thesis-writing workflow

- **Read `paper/references/adviser-log.md` first** before giving thesis direction; the newest entry (top) wins. Scope as of 2026-08-31: capture user mannerisms from **short** mouse signals/trajectories, not long sessions. "Short signal" and which mannerisms to prioritize are still open questions.
- When the user shares adviser feedback, add a dated entry to the **top** of the adviser log using the template in that file.
- Skills in `.agents/skills/` (mirrored at root `SKILL.md`): `mouse-biometrics-thesis` (domain + adviser log), `academic-writing` (tone, chapter templates), `humanize-academic-writing` (burstiness / anti-cliché rules). Follow them for chapter drafting, and run `paper/tools/audit_writing.py` on drafts.
- Citations are IEEE style. Only cite papers that exist in `paper/references/` (`rrl-candidate-papers.md`, `measurement-comparison-survey.md`, `new-candidates.md`) or that the user provides; never fabricate references.
- `paper/references/plan.md` logs completed task plans; append a new plan section when finishing a sizable paper task.
- `paper/references/annotated-bibliography.md` was **deleted** in commit `571a828`, but the skills and `example-rrl-fetch.py` still reference it (the fetcher warns and continues without filtering known papers). `paper/references/pipeline.md` is referenced but never existed. Tell the user if a task depends on them; don't invent their contents.
- `example-rrl-fetch.py` resolves its bibliography and `new-candidates.md` relative to its own directory — keep it inside `paper/references/`.
- `temp.md` is a local scratch prompt (git-ignored), not project content.

## Git and CI

- Remote: `github.com/chrjym/thesis-mouse-biometrics`. Default branch `main`; feature work happens on branches (e.g. `chrjym1`).
- `.github/workflows/literature-checker.yml` runs every Monday 00:00 UTC (and on manual dispatch) and **pushes commits to `main`** from `github-actions[bot]` updating `paper/references/new-candidates.md`. Pull before pushing to `main`, and expect conflicts in that file. If you move `example-rrl-fetch.py` or `new-candidates.md`, update the workflow paths too.
- Commit locally after every completed change with a descriptive message; never push unless asked.
- Commit messages must contain **no names**: no `Co-Authored-By` trailer, no tool or person attribution (user instruction, 2026-10-08).
- Don't commit `__pycache__/`, `.venv/`/`venv/`, or notebook checkpoints (see root `.gitignore`).
