# Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication

[![Python 3.11](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![Status: Experimental Model](https://img.shields.io/badge/Status-Experimental%20Model-orange.svg)]()
[![Domain: Behavioral Biometrics](https://img.shields.io/badge/Domain-Continuous%20Authentication-green.svg)]()

Undergraduate thesis repository: research notes, benchmark datasets, data-processing scripts, and exploratory notebooks for a continuous authentication model that identifies users from short mouse trajectory strokes.

**Contents**

1. [Overview](#1-overview)
2. [Proposed Pipeline](#2-proposed-pipeline)
3. [Current Status](#3-current-status)
4. [Quick Start](#4-quick-start)
5. [Datasets](#5-datasets)
6. [Data-Processing Scripts](#6-data-processing-scripts)
7. [Notebooks](#7-notebooks)
8. [Research and Writing Tools](#8-research-and-writing-tools)
9. [Repository Layout](#9-repository-layout)
10. [Baseline References](#10-baseline-references)

---

## 1. Overview

Passwords, PINs, and static biometrics verify a user once, at login. After that, the operating system cannot tell whether the same person is still at the keyboard. It is blind to console takeovers, session hijacking, and injected input.

This thesis studies an **explainable, continuous authentication model** that checks identity passively for the whole session. It does not aggregate statistics over several minutes or rely on a black-box deep model. Instead, it takes **behavioral fingerprints from short, sub-second mouse strokes** using closed-form differential geometry, convex hull bounding, Discrete Fréchet distance, and dynamic thresholding.

---

## 2. Proposed Pipeline

```
Short-Signal Capture → Closed-Form Geometry → Convex Hull Bounding → Fréchet Morphometry → Dynamic Thresholding
```

| Stage | What it does |
| :--- | :--- |
| **1. Short-signal capture** | Split continuous mouse movement into atomic point-to-point strokes (under 1 s) at clicks, pauses, or sharp direction reversals. |
| **2. Closed-form geometry** | Per stroke: **orthogonal chord deviation** ($d_\perp$, distance from the start–end chord), **discrete Menger curvature** ($\kappa$, circumcircle curvature of point triplets, which captures tremor and inflection), and **straightness ratio** ($S$, net displacement ÷ path length). Guards against division by zero and collinear points. |
| **3. Convex hull bounding** | Fit a minimal 2D polygon around the stroke to capture spatial dispersion, path variance, and overshoot. |
| **4. Fréchet morphometry** | Compare a candidate stroke with the user's enrolled profile using **Discrete Fréchet distance** ($\delta_F$). Point order is preserved, avoiding the velocity distortion of elastic time warping. |
| **5. Dynamic thresholding** | Feed dissimilarity scores into a per-action trust accumulator with a calibrated threshold. Slow drift (such as fatigue) is tolerated; sudden anomalous sequences are flagged. |

---

## 3. Current Status

| Component | Status |
| :--- | :--- |
| Literature review, survey, and Chapter 1 draft | Done (see [paper/references/](paper/references/)) |
| Balabit and SapiMouse datasets in the repo | Done |
| First-movement capture (first `Move`/`Drag` point per session) | Done. Outputs are in [experiments/outputs/](experiments/outputs/) |
| Per-user first-movement visualization notebooks | Done for the 10 Balabit users (training and test) |
| Full stroke extraction to Parquet | Script written ([experiments/scripts/combine_balabit_strokes.py](experiments/scripts/combine_balabit_strokes.py)) |
| Stages 2–5 (geometry, convex hull, Fréchet, thresholding) | Not started |
| FAR / FRR / EER evaluation | Not started |

> [!NOTE]
> The capture scripts accept `--min-step-px`, `--sustain-points`, `--idle-ms`, and `--max-duration-ms`. These values are **only recorded** in each output JSON (`capture_rule`). The capture itself still keeps just the first `Move`/`Drag` point (`capture_phase: "first_point_only"`).

---

## 4. Quick Start

Requires Python 3.11+.

```bash
git clone https://github.com/chrjym/thesis-mouse-biometrics.git
cd thesis-mouse-biometrics

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # pandas, pyarrow, matplotlib, jupyter, ipykernel
```

The raw Balabit and SapiMouse session files are already committed under [experiments/data/](experiments/data/), so the scripts run immediately after cloning. Run every script from the repository root.

```bash
# Example: flatten every stroke for Balabit user7 into a Parquet table
python experiments/scripts/combine_balabit_strokes.py --user user7
```

---

## 5. Datasets

See [experiments/data/README.md](experiments/data/README.md) for download sources and full column descriptions, and [experiments/data/balabit/README.md](experiments/data/balabit/README.md) for the original challenge description.

| Dataset | Location | Users | Sessions in repo | Timestamp unit | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Balabit Mouse Dynamics Challenge** | `experiments/data/balabit/training_files/` | 10 | 65 (genuine only) | seconds | Enrollment / training |
| | `experiments/data/balabit/test_files/` | 10 | 1,611 (genuine + impostor) | seconds | Evaluation. Labels for the public part are in `experiments/data/balabit/public_labels.csv` |
| **SapiMouse** | `experiments/data/sapimouse/` | 120 | 245 (one 1-min + one 3-min per user) | milliseconds | Supplementary benchmark |

Balabit user IDs are `user7`, `user9`, `user12`, `user15`, `user16`, `user20`, `user21`, `user23`, `user29`, and `user35`.

**Raw columns** (as they appear in the files):

- Balabit: `record timestamp, client timestamp, button, state, x, y`. Session files have no extension.
- SapiMouse: `client timestamp, button, state, x, y`

`state` is one of `Move`, `Drag`, `Pressed`, or `Released`. The scripts read `client timestamp` and convert it to milliseconds.

---

## 6. Data-Processing Scripts

All scripts live in [experiments/scripts/](experiments/scripts/), use `argparse` (pass `--help` for options), and resolve default paths relative to the `experiments/` folder, so they work from any working directory.

### 6.1 First-movement capture

[experiments/scripts/capture_first_movement.py](experiments/scripts/capture_first_movement.py) is the shared library. For every `<input-dir>/<user>/<session>` file, it writes `<output-dir>/<user>/<session>.json` containing the first `Move`/`Drag` point, plus a `summary.json` index for the whole run.

| Script | Dataset | Default input |
| :--- | :--- | :--- |
| [automate_balabit.py](experiments/scripts/automate_balabit.py) | Balabit training | `experiments/data/balabit/training_files` |
| [automate_balabit_test_first_movement.py](experiments/scripts/automate_balabit_test_first_movement.py) | Balabit test | `experiments/data/balabit/test_files` |
| [automate_sapimouse.py](experiments/scripts/automate_sapimouse.py) | SapiMouse (`*.csv`) | `experiments/data/sapimouse` |

The committed outputs were produced with these output directories. Use the same commands to regenerate them:

```bash
python experiments/scripts/automate_balabit.py \
    --output-dir experiments/outputs/balabit_training_files_first_movements

python experiments/scripts/automate_balabit_test_first_movement.py \
    --output-dir experiments/outputs/balabit_test_files_first_movements

python experiments/scripts/automate_sapimouse.py        # default: experiments/outputs/sapimouse_first_movements
```

Each per-session JSON looks like this:

```json
{
  "source_file": ".../data/balabit/training_files/user7/session_...",
  "timestamp_unit": "milliseconds",
  "capture_phase": "first_point_only",
  "capture_rule": {"min_step_px": 3.0, "sustain_points": 3, "idle_ms": 100.0, "max_duration_ms": 1000.0},
  "point_count": 1,
  "start_timestamp_ms": 0.0,
  "end_timestamp_ms": 0.0,
  "points": [{"timestamp_ms": 0.0, "x": 126.0, "y": 337.0, "event_type": "Move", "button": "NoButton"}]
}
```

> [!NOTE]
> The committed `summary.json` files contain absolute paths from the machine that generated them (`/home/tin/...`). Rerunning the scripts rewrites them with your own paths.

### 6.2 Full stroke extraction

[experiments/scripts/combine_balabit_strokes.py](experiments/scripts/combine_balabit_strokes.py) flattens **every** stroke for one or more Balabit users into a single Parquet file. A new stroke starts at the first `Move`/`Drag` event after a `Pressed`/`Released` event, so each stroke is the movement between clicks.

```bash
# One user (defaults: training files → experiments/outputs/balabit_user7_strokes.parquet)
python experiments/scripts/combine_balabit_strokes.py --user user7

# Several users, from the test set, to a custom file
python experiments/scripts/combine_balabit_strokes.py --user user7 --user user9 \
    --input-dir experiments/data/balabit/test_files \
    --output experiments/outputs/balabit_test_user7_user9_strokes.parquet
```

Output columns: `user_id, session_id, stroke_id, point_index, x, y, timestamp_ms, event_type, button`. `stroke_id` restarts at 1 in each session, so identify a stroke by `(user_id, session_id, stroke_id)`.

> [!TIP]
> The default `--output` path says `user7` whatever `--user` you pass. Set `--output` explicitly when you extract other users.

### 6.3 Notebook generator

[experiments/scripts/automate_balabit_test_first_movement_patterns.py](experiments/scripts/automate_balabit_test_first_movement_patterns.py) writes one visualization notebook per user from a first-movement output folder:

```bash
python experiments/scripts/automate_balabit_test_first_movement_patterns.py \
    --input-dir experiments/outputs/balabit_test_files_first_movements \
    --notebook-dir experiments/notebooks/balabit_test_files_first_movement_patterns

# Limit to specific users
python experiments/scripts/automate_balabit_test_first_movement_patterns.py --user user7 --user user9 \
    --input-dir experiments/outputs/balabit_training_files_first_movements \
    --notebook-dir experiments/notebooks/balabit_training_files_first_movement_patterns
```

---

## 7. Notebooks

```bash
jupyter notebook experiments/notebooks/
```

| Notebook | Purpose |
| :--- | :--- |
| `experiments/notebooks/balabit_training_files_first_movement_patterns/<user>/visualize_<user>.ipynb` | Plots the first-movement point of every **training** session for one user, in session order. |
| `experiments/notebooks/balabit_test_files_first_movement_patterns/<user>/visualize_<user>.ipynb` | Same plot for the **test** sessions (genuine and impostor mixed). |
| [experiments/notebooks/test_only.ipynb](experiments/notebooks/test_only.ipynb) | Scratch notebook used to prototype the plots before the generator script. Change `USER_ID` to inspect another user. |

The generated notebooks find their data by searching upward for the folder that contains `outputs/` (that is, `experiments/`), so they work from any working directory inside it. Run the capture scripts first if `experiments/outputs/` is missing.

---

## 8. Research and Writing Tools

Everything for the written thesis lives in [paper/](paper/).

### Literature

| File | Contents |
| :--- | :--- |
| [paper/references/rrl-candidate-papers.md](paper/references/rrl-candidate-papers.md) | 20 curated, fact-checked RRL sources (2018–2026) |
| [paper/references/measurement-comparison-survey.md](paper/references/measurement-comparison-survey.md) | Survey of mouse-dynamics measurements and matching methods, compared with this thesis's approach |
| [paper/references/new-candidates.md](paper/references/new-candidates.md) | New papers found by the literature checker (newest first) |
| [paper/references/background_pure_paragraphs.md](paper/references/background_pure_paragraphs.md) | Chapter 1 Background of the Study draft (IEEE citations) |
| [paper/references/adviser-log.md](paper/references/adviser-log.md) | Adviser feedback, scope guidance, and decisions. **Check this before changing direction.** |
| [paper/references/plan.md](paper/references/plan.md) | Completed task plans and their deliverables |
| [Literature_Review_Mouse_Biometrics.xlsx](paper/Literature_Review_Mouse_Biometrics.xlsx) | Group literature review spreadsheet |

**Literature checker.** [paper/references/example-rrl-fetch.py](paper/references/example-rrl-fetch.py) queries arXiv, OpenAlex, Semantic Scholar, and (optionally) Google Scholar through SerpApi. It removes duplicates, filters out papers already in the bibliography, and prepends new ones to `paper/references/new-candidates.md`.

```bash
python paper/references/example-rrl-fetch.py
python paper/references/example-rrl-fetch.py --queries "mouse dynamics continuous authentication"
python paper/references/example-rrl-fetch.py --dry-run     # preview without writing new-candidates.md
export SERPAPI_KEY=...   # optional, enables Google Scholar
```

The [.github/workflows/literature-checker.yml](.github/workflows/literature-checker.yml) workflow runs the checker every Monday at 00:00 UTC (or manually from the Actions tab) and commits any new candidates. Add `SERPAPI_KEY` as a repository secret to include Google Scholar.

### Writing auditor

[paper/tools/audit_writing.py](paper/tools/audit_writing.py) is an offline check of chapter drafts. It flags uniform sentence lengths (low burstiness), stock LLM phrases, and other patterns that AI detectors pick up.

```bash
python paper/tools/audit_writing.py paper/references/background_pure_paragraphs.md          # summary
python paper/tools/audit_writing.py paper/references/background_pure_paragraphs.md -v       # per paragraph
python paper/tools/audit_writing.py paper/references/background_pure_paragraphs.md --json   # machine-readable
```

### AI assistant skills

[SKILL.md](SKILL.md) and [.agents/skills/](.agents/skills/) hold instructions for AI coding and writing assistants: thesis domain context (`mouse-biometrics-thesis`), academic tone and chapter templates (`academic-writing`), and natural writing cadence (`humanize-academic-writing`).

---

## 9. Repository Layout

The repository is split into two working folders: **`paper/`** for the written research and **`experiments/`** for code, inputs, and outputs.

```
thesis-mouse-biometrics/
├── README.md
├── SKILL.md                                       # Thesis assistant skill (domain context for AI tools)
├── requirements.txt
│
├── paper/                                         # ── RESEARCH PAPER ──
│   ├── references/                                # Literature, survey, chapter drafts, adviser log
│   │   ├── adviser-log.md
│   │   ├── background_pure_paragraphs.md          # Chapter 1 draft
│   │   ├── measurement-comparison-survey.md
│   │   ├── rrl-candidate-papers.md
│   │   ├── new-candidates.md
│   │   ├── literature-sources.md
│   │   ├── plan.md
│   │   └── example-rrl-fetch.py                   # Literature checker (writes next to itself)
│   ├── tools/
│   │   └── audit_writing.py                       # Writing cadence auditor
│   └── Literature_Review_Mouse_Biometrics.xlsx
│
├── experiments/                                   # ── SCRIPTS, INPUTS, OUTPUTS ──
│   ├── data/                                      # INPUT: raw benchmark datasets (see data/README.md)
│   │   ├── balabit/
│   │   │   ├── training_files/<user>/session_*    # 10 users, genuine sessions
│   │   │   ├── test_files/<user>/session_*        # 10 users, mixed genuine/impostor
│   │   │   └── public_labels.csv
│   │   └── sapimouse/<user>/session_*_{1,3}min.csv  # 120 users
│   ├── scripts/
│   │   ├── capture_first_movement.py              # Shared first-movement capture library
│   │   ├── automate_balabit.py                    # Capture: Balabit training
│   │   ├── automate_balabit_test_first_movement.py  # Capture: Balabit test
│   │   ├── automate_sapimouse.py                  # Capture: SapiMouse
│   │   ├── automate_balabit_test_first_movement_patterns.py  # Generate per-user notebooks
│   │   └── combine_balabit_strokes.py             # All strokes → Parquet
│   ├── outputs/                                   # OUTPUT: per-session JSON + summary.json
│   │   ├── balabit_training_files_first_movements/
│   │   ├── balabit_test_files_first_movements/
│   │   └── sapimouse_first_movements/
│   └── notebooks/
│       ├── balabit_training_files_first_movement_patterns/<user>/visualize_<user>.ipynb
│       ├── balabit_test_files_first_movement_patterns/<user>/visualize_<user>.ipynb
│       └── test_only.ipynb
│
├── .agents/skills/                                # Academic-writing and thesis skills for AI assistants
├── .github/workflows/literature-checker.yml       # Weekly literature fetch
└── .obsidian/                                     # Obsidian vault settings (notes viewing)
```

---

## 10. Baseline References

- M. A. Khan et al., "Mouse Dynamics Behavioral Biometrics: A Survey of Methodologies, Challenges, and Opportunities," *ACM Computing Surveys*, 2024.
- Y. Wang et al., "Optimizing Mouse Dynamics for User Authentication: LT-AMouse via Mouse Authentication Units," *arXiv:2504.21415*, 2025.
- M. Djioua and R. Plamondon, "Kinematic Neuromotor Modeling of Rapid Mouse Trajectory Strokes," *IEEE TSMC*, 2019.
- E. Asgarov, "Mathematical Feature Representations of Mouse Dynamics," *JPIT*, 2026.
- H. Alt and M. Godau, "Computing the Fréchet distance between two polygonal curves," *IJFCS*, 1995.
- Á. Fülöp, L. Kovács, T. Kurics, and E. Windhager-Pokol, *Balabit Mouse Dynamics Challenge data set*, 2016. https://github.com/balabit/Mouse-Dynamics-Challenge
