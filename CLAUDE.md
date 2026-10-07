# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

An undergraduate thesis (4-member group): **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication."** It is half writing, half experiments:

- `paper/` — the written research: literature, survey, chapter drafts, adviser log, and writing tools.
- `experiment_earl/` — Python scripts, TOML config, and raw datasets. This is the **only** experiments folder; the old `experiments/` folder (first-movement capture, stroke extraction, notebooks, committed outputs) was removed in commit `d10f50c` and lives on in git history (e.g. `f36850c`).

The originally proposed method (5 stages: short-stroke segmentation → closed-form geometry → convex hull bounding → Discrete Fréchet distance → dynamic trust threshold) is **not implemented**. What runs now is Earl's idea (see `EARL_IDEA.md`): split each session into 1-second chunks shifted to (0, 0), flag burn-in chunks, and build each user's profile from 3 random training sessions, then benchmark two profile models on the Balabit test set: the **concave hull** of chunk end points (adviser instruction) versus a **One-Class SVM** on per-chunk path features. Metric is EER over sliding windows of moving seconds.

`README.md` still describes the deleted `experiments/` layout and is out of date; trust this file and the code.

## Commands

Run from the repo root. There is no build, test suite, or linter.

```bash
pip install -r requirements.txt     # pandas, pyarrow, shapely, matplotlib, jupyter, ipykernel, scikit-learn

# Hull profiles: 3 random training sessions per user -> vectors/chunks CSVs, profile.json, profile.png
python experiment_earl/scripts/main.py [--user user15] [--sessions 3] [--seed 0] [--idle-seconds 5] [--concave-ratio 0.1]

# Benchmark One-Class SVM vs concave hull (all settings live in the TOML; copy it per experiment)
python experiment_earl/scripts/benchmark_ocsvm.py [--config experiment_earl/configs/ocsvm.toml]

# Paper tools
python paper/tools/audit_writing.py <draft.md> [-v] [--json]   # AI-detector cadence audit
python paper/references/example-rrl-fetch.py [--dry-run] [--queries ...]
```

`main.py` writes under `experiment_earl/outputs/<user>/` (per-session `session_*/` CSVs are git-ignored because they regenerate in seconds). `benchmark_ocsvm.py` writes `outputs/benchmark_ocsvm.json` containing the config used, mean EER, timing/memory, and per-user results. To validate `chunking.py` changes, regenerate for `experiment_earl/temp/` reference CSVs (`vectors.csv`, `chunks.csv`, Earl's prototype output for test session `user15/session_0003960194`); they must match exactly.

**Working-tree caveat:** at the time of writing, `experiment_earl/scripts/`, `configs/`, and `temp/` are committed in `HEAD` but deleted (uncommitted) in the working tree. If they are missing, `git restore experiment_earl` before running anything; don't recreate them from scratch.

## Code architecture (`experiment_earl/scripts/`)

- `chunking.py` — library. `load_session` reads a raw Balabit file in file order and drops x/y ≥ 65535 glitches. `second_boundaries` picks, for each second t, the first event with `record timestamp` ≥ t via `np.searchsorted`. `build_vectors` → per-second positions; `build_chunks` → chunk t = position(t+1) − position(t), start shifted to (0, 0); `mark_burn_in` flags the first moving chunk of a session and the first moving chunk after `idle_seconds` idle chunks (recorded but **not used** to filter yet).
- `main.py` — hull profile builder. Samples sessions with `random.Random(f"{seed}-{user}")`, concatenates chunk end points, takes shapely `convex_hull` and `concave_hull(ratio)`, writes `profile.json`/`profile.png`/`summary.json`.
- `features.py` — per-chunk *path* features (`FEATURES`: dx, dy, path_length, straightness, mean_speed, max_speed, curvature, total_turning, direction_changes, pauses). Uses `client timestamp` (~16 ms) for speed, and optionally `resample` to a common time grid (hold last position, no interpolation) so the ~16 ms vs ~110 ms loggers are comparable. Only chunks where the cursor moved are kept.
- `benchmark_ocsvm.py` — reads `configs/ocsvm.toml`; per user: enroll on the same seeded 3 sessions as `main.py`, fit sklearn pipeline (column select → log transform → robust/standard scaler → `OneClassSVM`), score labelled test sessions from `public_labels.csv`, and report EER per window size (`0` = whole session) plus an optional hull baseline built from (dx, dy) of the same training chunks. Only users/sessions with public labels are evaluated.

Scripts import siblings as plain modules (`from chunking import ...`), which works because Python puts the script's directory on `sys.path`. Keep new scripts in the same folder.

### Conventions to match

- Each script: shebang + one-line module docstring, `argparse` with `description=__doc__`, `ROOT = Path(__file__).resolve().parents[1]` (resolves to `experiment_earl/`), defaults built from `ROOT`, `main()` that prints a short summary (counts + output path).
- Experiment settings go in the TOML with explanatory comments, not as new CLI flags; the used config is saved inside the output JSON.
- Use the stdlib `csv.DictReader` for raw session files; numpy for the numeric work.
- Chunk pipeline keeps `t`/`t_plus_1` in seconds of `record timestamp`.
- Small, plain functions; type hints on signatures; sparse comments.

## Data facts that are easy to get wrong

Datasets are under `experiment_earl/datasets/` and are committed to git (~1,900 session files).

- **Balabit** session files have **no extension** (`session_0032069206`); glob with `*`. Columns: `record timestamp, client timestamp, button, state, x, y`. Timestamps are **seconds** (floats). `training_files` (65 sessions) are genuine only; `test_files` (1,611) mix genuine and impostor; `public_labels.csv` labels only 816 of them (`is_illegal = 1` for impostors).
- **SapiMouse** (`datasets/sapimouse/`, 120 users, 245 files `session_<date>_{1min,3min}.csv`): columns `client timestamp, button, state, x, y`, timestamps in **milliseconds**. No script uses it currently.
- `state ∈ {Move, Drag, Pressed, Released}`. `y` grows downward (screen coordinates) — plots call `invert_yaxis()`.
- Balabit users: `user7, user9, user12, user15, user16, user20, user21, user23, user29, user35`.
- Some Balabit rows have **x = y = 65535** (logging glitches, not positions). Drop them before any spatial computation or they create ~60,000 px jumps.
- Balabit `record timestamp` has ~0.1 s resolution, so ~90% of rows tie with a neighbor; `client timestamp` is ~16 ms and steps backward in one session (`features.resample` handles it with `maximum.accumulate`). Don't re-sort: pandas' default sort is unstable and reorders ties. Use file order or a stable sort.
- Sampling rate and screen size differ by user: user7/9/20 log every ~16 ms, the rest every ~110 ms; screens range from 1280×800 (user23) to 1920×1080 (user15/16). Per-point features and hull extents partly measure these rather than behavior. Resample/normalize before claiming user differences.
- `experiment_earl/temp/` example session is a **test** session labelled impostor, not user15's genuine data. Don't build profiles from it.

## Thesis-writing workflow

- **Read `paper/references/adviser-log.md` first** before giving thesis direction; the newest entry (top) wins. Scope as of 2026-08-31: capture user mannerisms from **short** mouse signals/trajectories, not long sessions. "Short signal" and which mannerisms to prioritize are still open questions.
- When the user shares adviser feedback, add a dated entry to the **top** of the adviser log using the template in that file.
- Skills in `.agents/skills/` (mirrored at root `SKILL.md`): `mouse-biometrics-thesis` (domain + adviser log), `academic-writing` (tone, chapter templates), `humanize-academic-writing` (burstiness / anti-cliché rules). Follow them for chapter drafting, and run `paper/tools/audit_writing.py` on drafts.
- Citations are IEEE style. Only cite papers that exist in `paper/references/` (`rrl-candidate-papers.md`, `measurement-comparison-survey.md`, `new-candidates.md`) or that the user provides; never fabricate references.
- `paper/references/plan.md` logs completed task plans; append a new plan section when finishing a sizable paper task.
- `paper/references/annotated-bibliography.md` was **deleted** in commit `571a828`, but the skills and `example-rrl-fetch.py` still reference it (the fetcher warns and continues without filtering known papers). `paper/references/pipeline.md` is referenced but never existed. Tell the user if a task depends on them; don't invent their contents.
- `example-rrl-fetch.py` resolves its bibliography and `new-candidates.md` relative to its own directory — keep it inside `paper/references/`.
- `EARL_IDEA.md` holds Earl's pipeline notes plus a pasted peer-reviewer persona prompt; `temp.md` is a local scratch prompt, not project content.

## Git and CI

- Remote: `github.com/chrjym/thesis-mouse-biometrics`. Default branch `main`; feature work happens on branches (e.g. `chrjym1`).
- `.github/workflows/literature-checker.yml` runs every Monday 00:00 UTC (and on manual dispatch) and **pushes commits to `main`** from `github-actions[bot]` updating `paper/references/new-candidates.md`. Pull before pushing to `main`, and expect conflicts in that file. If you move `example-rrl-fetch.py` or `new-candidates.md`, update the workflow paths too.
- Commit locally after every completed change with a descriptive message; never push unless asked.
- Don't commit `__pycache__/`, `.venv/`/`venv/`, or notebook checkpoints (see root `.gitignore`).
