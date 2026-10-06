# CLAUDE.md

Guidance for Claude Code when working in this repository. For the project overview, dataset tables, and full script usage, see [README.md](README.md).

## What this repo is

An undergraduate thesis (4-member group): **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication."** It is half writing, half experiments:

- `paper/` — the written research: literature, survey, chapter drafts, adviser log, and writing tools.
- `experiments/` — Python scripts, raw datasets (input), generated captures (output), and Jupyter notebooks.

The proposed method (not yet implemented) is a 5-stage pipeline: short-stroke segmentation → closed-form geometry (orthogonal chord deviation, discrete Menger curvature, straightness ratio) → convex hull bounding → Discrete Fréchet distance against an enrolled profile → dynamic trust threshold. **Only data capture/visualization exists so far**; stages 2–5 and FAR/FRR/EER evaluation are future work.

## Commands

Run from the repo root. There is no build, test suite, or linter.

```bash
pip install -r requirements.txt     # pandas, pyarrow, matplotlib, jupyter, ipykernel

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

# Paper tools
python paper/tools/audit_writing.py <draft.md> [-v] [--json]   # AI-detector cadence audit
python paper/references/example-rrl-fetch.py [--dry-run] [--queries ...]
```

To sanity-check a script change without touching committed outputs, point `--output-dir`/`--output` at a scratch directory and confirm the `processed`/`failed` counts (expected: Balabit training 65, test 1,611, SapiMouse 245, all with 0 failed).

## Code architecture (`experiments/scripts/`)

- `capture_first_movement.py` is the shared library. `capture_directory(input_dir, output_dir, pattern, timestamp_unit, settings)` walks `<input>/<user>/<session>`, writes `<output>/<user>/<session>.json` per session plus `<output>/summary.json`.
- `automate_balabit.py`, `automate_balabit_test_first_movement.py`, `automate_sapimouse.py` are thin CLI wrappers around it; they differ only in default paths, glob pattern, and timestamp unit (`"seconds"` for Balabit, `"milliseconds"` for SapiMouse).
- `combine_balabit_strokes.py` is standalone (does not use the library). A stroke = consecutive `Move`/`Drag` rows; any `Pressed`/`Released` row ends the current stroke. `stroke_id` restarts at 1 per session, so a stroke's key is `(user_id, session_id, stroke_id)`.
- `automate_balabit_test_first_movement_patterns.py` emits `.ipynb` JSON directly (notebook cells are Python string lists inside the script). Edit the generator, not the generated notebooks, then regenerate.

The wrappers import the library as a sibling module (`from capture_first_movement import ...`), which works because Python puts the script's directory on `sys.path`. Keep new scripts in the same folder or adjust imports.

### Conventions to match

- Each script: shebang + one-line module docstring, `argparse` with `description=__doc__`, `ROOT = Path(__file__).resolve().parents[1]` (resolves to `experiments/`), defaults built from `ROOT`, `main()` that prints a short summary (counts + output path).
- Use the stdlib `csv.DictReader` for raw session files; pandas only for tabular output.
- Normalize all timestamps to **milliseconds** (`timestamp_ms`) in outputs.
- Output point records use the keys `timestamp_ms, x, y, event_type, button`.
- Small, plain functions; type hints on signatures; sparse comments.

## Data facts that are easy to get wrong

- **Balabit** session files have **no extension** (`session_0032069206`); glob with `*`, not `*.csv`. Columns: `record timestamp, client timestamp, button, state, x, y`. Timestamps are **seconds** (floats).
- **SapiMouse** files are `session_<date>_{1min,3min}.csv`. Columns: `client timestamp, button, state, x, y` (no `record timestamp`). Timestamps are **milliseconds**.
- Both use `client timestamp` (with a space) and `state ∈ {Move, Drag, Pressed, Released}`. `y` grows downward (screen coordinates) — plots call `invert_yaxis()`.
- Balabit users: `user7, user9, user12, user15, user16, user20, user21, user23, user29, user35`. `training_files` are genuine only; `test_files` mix genuine and impostor sessions; `public_labels.csv` labels only the public subset of test sessions.
- `experiments/data/README.md` is partly inaccurate (claims raw data is gitignored, Balabit timestamps in ms, SapiMouse column `timestamp`). Trust the files themselves and this document.
- Raw data **is committed** to git (~1,900 session files). `experiments/data/.gitignore` patterns are written relative to the repo root, so they don't actually match anything.

## Known gotchas

- The capture flags `--min-step-px`, `--sustain-points`, `--idle-ms`, `--max-duration-ms` are **recorded but unused**: output is always just the first `Move`/`Drag` point (`capture_phase: "first_point_only"`). Don't describe them as active filters; implementing them is open work.
- Script default `--output-dir` names (e.g. `outputs/balabit_test_first_movements`) differ from the committed folders (`outputs/balabit_test_files_first_movements`). Pass `--output-dir` explicitly to overwrite the committed outputs.
- `combine_balabit_strokes.py` defaults `--output` to `balabit_user7_strokes.parquet` regardless of `--user`.
- Committed `summary.json` files contain another machine's absolute paths (`/home/tin/...`); regenerating rewrites them.
- `paper/references/annotated-bibliography.md` was **deleted** in commit `571a828`, but `SKILL.md`, the thesis skill, and `example-rrl-fetch.py` still reference it. The fetcher prints a warning and continues **without** filtering out known papers. `paper/references/pipeline.md` is referenced by the skills but never existed. Tell the user if a task depends on these files; don't invent their contents.
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
- Don't commit `__pycache__/`, `.venv/`, or notebook checkpoints (see root `.gitignore`). `temp.md` is a local scratch prompt, not project content.
