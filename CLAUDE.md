# CLAUDE.md

Guidance for Claude Code when working in this repository. For the project overview, dataset tables, and full script usage, see [README.md](README.md).

## What this repo is

An undergraduate thesis (4-member group): **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication."** It is half writing, half experiments:

- `paper/` — the written research: literature, survey, chapter drafts, adviser log, and writing tools.
- `experiments/` — Python scripts, raw datasets (input), generated captures (output), and Jupyter notebooks.

The proposed method (not yet implemented) is a 5-stage pipeline: short-stroke segmentation → closed-form geometry (orthogonal chord deviation, discrete Menger curvature, straightness ratio) → convex hull bounding → Discrete Fréchet distance against an enrolled profile → dynamic trust threshold. **Only data capture/visualization exists so far**; stages 2–5 and FAR/FRR/EER evaluation are future work.

A parallel idea from a group member (Earl; prototype in `experiments/initial_program/`) is now in the pipeline: split sessions into 1-second chunks shifted to (0, 0), flag burn-in chunks (movement at session start or after a long idle), and build each user's **initial profile** as the convex → concave hull of chunk endpoints from 3 random training sessions (an adviser instruction). Matching new sessions against the profile is not built yet.

## Commands

Run from the repo root. There is no build, test suite, or linter.

```bash
pip install -r requirements.txt     # pandas, pyarrow, shapely, matplotlib, jupyter, ipykernel

# First-movement capture (committed outputs used these --output-dir values)
python experiments/scripts/automate_balabit.py --output-dir experiments/outputs/balabit_training_files_first_movements
python experiments/scripts/automate_balabit_test_first_movement.py --output-dir experiments/outputs/balabit_test_files_first_movements
python experiments/scripts/automate_sapimouse.py

# All strokes for selected Balabit users -> Parquet (needs pyarrow)
python experiments/scripts/combine_balabit_strokes.py --user user7 --output experiments/outputs/balabit_user7_strokes.parquet

# Regenerate per-user visualization notebooks from a capture folder
python experiments/scripts/automate_balabit_test_first_movement_patterns.py \
    --input-dir experiments/outputs/balabit_training_files_first_movements \
    --notebook-dir experiments/notebooks/balabit_training_files_first_movement_patterns

# Initial profiles: 1-second chunks of 3 random training sessions -> convex/concave hull (~6 s, all users)
python experiments/scripts/build_initial_profiles.py [--user user15] [--burn-in-only] [--idle-seconds 5] [--seed 0]

# Paper tools
python paper/tools/audit_writing.py <draft.md> [-v] [--json]   # AI-detector cadence audit
python paper/references/example-rrl-fetch.py [--dry-run] [--queries ...]
```

To sanity-check a script change without touching committed outputs, point `--output-dir`/`--output` at a scratch directory and confirm the `processed`/`failed` counts (expected: Balabit training 65, test 1,611, SapiMouse 245, all with 0 failed).

## Code architecture (`experiments/scripts/`)

- `capture_first_movement.py` is the shared library. `capture_directory(input_dir, output_dir, pattern, timestamp_unit, settings)` walks `<input>/<user>/<session>`, writes `<output>/<user>/<session>.json` per session plus `<output>/summary.json`.
- `automate_balabit.py`, `automate_balabit_test_first_movement.py`, `automate_sapimouse.py` are thin CLI wrappers around it; they differ only in default paths, glob pattern, and timestamp unit (`"seconds"` for Balabit, `"milliseconds"` for SapiMouse).
- `combine_balabit_strokes.py` is standalone (does not use the library). A stroke = consecutive `Move`/`Drag` rows; any `Pressed`/`Released` row ends the current stroke. `stroke_id` restarts at 1 per session, so a stroke's key is `(user_id, session_id, stroke_id)`.
- `chunk_by_second.py` is the 1-second chunking library (ported from `experiments/initial_program/`). Position at second t = first event with `record timestamp` >= t, found by `np.searchsorted` in file order; chunk t = position(t+1) − position(t). `mark_burn_in` flags the first moving chunk of a session and the first moving chunk after `idle_seconds` zero chunks.
- `build_initial_profiles.py` picks sessions with `random.Random(f"{seed}-{user}")`, writes `<user>/chunks.csv` (git-ignored, ~24 MB total) and `<user>/profile.json` (sessions, settings, counts, hull coordinates/areas) under `outputs/balabit_initial_profiles/`. Hulls use shapely (`concave_hull`, ratio 0.1). Visualized by `notebooks/initial_profiles.ipynb`.
- `automate_balabit_test_first_movement_patterns.py` emits `.ipynb` JSON directly (notebook cells are Python string lists inside the script). Edit the generator, not the generated notebooks, then regenerate.

The wrappers import the library as a sibling module (`from capture_first_movement import ...`), which works because Python puts the script's directory on `sys.path`. Keep new scripts in the same folder or adjust imports.

### Conventions to match

- Each script: shebang + one-line module docstring, `argparse` with `description=__doc__`, `ROOT = Path(__file__).resolve().parents[1]` (resolves to `experiments/`), defaults built from `ROOT`, `main()` that prints a short summary (counts + output path).
- Use the stdlib `csv.DictReader` for raw session files; pandas only for tabular output.
- Normalize all timestamps to **milliseconds** (`timestamp_ms`) in outputs. Exception: the chunk pipeline keeps `t`/`t_plus_1` in seconds of `record timestamp`, matching Earl's prototype.
- Output point records use the keys `timestamp_ms, x, y, event_type, button`.
- Small, plain functions; type hints on signatures; sparse comments.

## Data facts that are easy to get wrong

- **Balabit** session files have **no extension** (`session_0032069206`); glob with `*`, not `*.csv`. Columns: `record timestamp, client timestamp, button, state, x, y`. Timestamps are **seconds** (floats).
- **SapiMouse** files are `session_<date>_{1min,3min}.csv`. Columns: `client timestamp, button, state, x, y` (no `record timestamp`). Timestamps are **milliseconds**.
- Both use `client timestamp` (with a space) and `state ∈ {Move, Drag, Pressed, Released}`. `y` grows downward (screen coordinates) — plots call `invert_yaxis()`.
- Balabit users: `user7, user9, user12, user15, user16, user20, user21, user23, user29, user35`. `training_files` are genuine only; `test_files` mix genuine and impostor sessions; `public_labels.csv` labels only the public subset of test sessions.
- `experiments/data/README.md` is partly inaccurate (claims raw data is gitignored, Balabit timestamps in ms, SapiMouse column `timestamp`). Trust the files themselves and this document.
- Some Balabit rows have **x = y = 65535** (80 rows in training, 7 users): logging glitches, not positions. Drop them before any spatial computation or they create ~60,000 px jumps.
- Balabit `record timestamp` has ~0.1 s resolution, so ~90% of rows tie with a neighbor; `client timestamp` is ~16 ms. It never decreases within a file, so don't re-sort (pandas' default sort is unstable and reorders ties). Use a stable sort or file order.
- Sampling rate and screen size differ by user: user7/9/20 log every ~16 ms, the rest every ~110 ms; screens range from 1280×800 (user23) to 1920×1080 (user15/16). Per-point features (curvature, point counts) and hull extents partly measure these rather than behavior. Resample/normalize before claiming user differences.
- Raw data **is committed** to git (~1,900 session files). `experiments/data/.gitignore` patterns are written relative to the repo root, so they don't actually match anything.

## Known gotchas

- The capture flags `--min-step-px`, `--sustain-points`, `--idle-ms`, `--max-duration-ms` are **recorded but unused**: output is always just the first `Move`/`Drag` point (`capture_phase: "first_point_only"`). Don't describe them as active filters; implementing them is open work.
- Script default `--output-dir` names (e.g. `outputs/balabit_test_first_movements`) differ from the committed folders (`outputs/balabit_test_files_first_movements`). Pass `--output-dir` explicitly to overwrite the committed outputs.
- `combine_balabit_strokes.py` defaults `--output` to `balabit_user7_strokes.parquet` regardless of `--user`.
- Committed `summary.json` files contain another machine's absolute paths (`/home/tin/...`); regenerating rewrites them.
- `paper/references/annotated-bibliography.md` was **deleted** in commit `571a828`, but `SKILL.md`, the thesis skill, and `example-rrl-fetch.py` still reference it. The fetcher prints a warning and continues **without** filtering out known papers. `paper/references/pipeline.md` is referenced by the skills but never existed. Tell the user if a task depends on these files; don't invent their contents.
- `experiments/initial_program/` is Earl's original prototype, kept untracked (its 135 MB `venv/` is git-ignored). Its example session `user15/session_0003960194.csv` is a **test** session labelled impostor, not user15's genuine data. Don't build profiles from it.
- `example-rrl-fetch.py` resolves its bibliography and `new-candidates.md` relative to its own directory — keep it inside `paper/references/`.

## Thesis-writing workflow

- **Read `paper/references/adviser-log.md` first** before giving thesis direction; the newest entry (top) wins. Current scope (2026-08-31): capture user mannerisms from **short** mouse signals/trajectories, not long sessions. "Short signal" and which mannerisms to prioritize are still open questions.
- When the user shares adviser feedback, add a dated entry to the **top** of the adviser log using the template in that file.
- Skills in `.agents/skills/` (mirrored at root `SKILL.md`): `mouse-biometrics-thesis` (domain + adviser log), `academic-writing` (tone, chapter templates), `humanize-academic-writing` (burstiness / anti-cliché rules). Follow them for chapter drafting, and run `paper/tools/audit_writing.py` on drafts.
- Citations are IEEE style. Only cite papers that exist in `paper/references/` (`rrl-candidate-papers.md`, `measurement-comparison-survey.md`, `new-candidates.md`) or that the user provides; never fabricate references.
- `paper/references/plan.md` logs completed task plans; append a new plan section when finishing a sizable paper task.

## Git and CI

- Remote: `github.com/chrjym/thesis-mouse-biometrics`. Default branch `main`; feature work happens on branches (e.g. `chrjym1`).
- `.github/workflows/literature-checker.yml` runs every Monday 00:00 UTC (and on manual dispatch) and **pushes commits to `main`** from `github-actions[bot]` updating `paper/references/new-candidates.md`. Pull before pushing to `main`, and expect conflicts in that file.
- If you move `paper/references/example-rrl-fetch.py` or `new-candidates.md`, update the workflow paths too.
- Commit locally after every completed change with a descriptive message; never push unless asked.
- Don't commit `__pycache__/`, `.venv/`/`venv/`, or notebook checkpoints (see root `.gitignore`). `temp.md` is a local scratch prompt, not project content.
