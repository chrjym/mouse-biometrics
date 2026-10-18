# Methodology pipeline

What this study does, step by step, from raw mouse logs to a verdict on the user. It describes the pipeline as
implemented and tested in `experiment_earl/` up to 2026-10-18, not the original proposal. Results are summarized in
[`experiment_earl/shape_results/README.md`](../../experiment_earl/shape_results/README.md).

**Aim.** Find out whether the geometric shape of a user's short mouse movements is personal enough to tell them
apart from other users, and so protect the legitimate user through continuous authentication.

**Scope.** Experimental only. Geometry (shape) is the main point. Short signals: a user's mannerism within a short
stroke (target ≈ 0.5 s). Explainable: every measure is a closed-form calculation.

## Overview

```
 1. Data            Balabit raw session logs (10 users, 114–253 sessions each)
        │
 2. Cleaning        drop scroll rows and glitch rows (x or y = 65535), stable time sort
        │
 3. Session draw    seeded shuffle per user → profile sessions | own test | impostor test
        │
 4. Segmentation    cut each session into short strokes at pauses and clicks
        │
 5. Normalization   start at (0, 0), scale to size 1, 64 points evenly spaced along the path
        │
 6. Profile         the user's strokes from k registration sessions
        │
 7. Comparison      new stroke vs profile: DTW / Euclidean / convex hull / geometric measures
        │
 8. Decision        stroke matches → session passes → user accepted or rejected
        │
 9. Evaluation      FRR, FAR, EER over users, splits and random draws
```

## 1. Data

- **Dataset:** Balabit Mouse Dynamics Challenge, 10 users (`user7, 9, 12, 15, 16, 20, 21, 23, 29, 35`).
- The original training and test files are merged into one folder per user (`datasets/balabit/users/<user>/`), 114–253
  sessions each. A session belongs to the user whose folder it is in; `public_labels.csv` is not used.
- Columns used: `client timestamp` (seconds), `button`, `state` (Move, Drag, Pressed, Released), `x`, `y`
  (screen pixels, y grows downward).

## 2. Cleaning

- Drop rows with missing time or position, scroll rows (no path), and glitch rows where x or y is 65535.
- Sort by time with a **stable** sort, because many timestamps tie, then set the first event to t = 0.

## 3. Session draw

One random draw from a fixed `seed` (945; repeated draws use 945–949) fixes every user's session order:
each user's sessions are shuffled once with `Random(f"{seed}-{user}")`.

| Role | Sessions used | Purpose |
|---|---|---|
| **Profile (registration)** | first k of the user's shuffled list | build the user's profile |
| **Own test** | last k of the user's list (never in a profile) | should be **accepted** |
| **Impostor test** | other users' sessions (never in this profile) | should be **rejected** |

Users are split into `n_legitimate` legitimate and `n_impostor` impostor users, with
`n_legitimate + n_impostor = 10`; the batch tests all 9 splits (1/9 … 9/1).

## 4. Segmentation into short strokes

A stroke is one movement between pauses or clicks:

$$\text{new stroke at point } i \iff t_i - t_{i-1} > \tau \;\lor\; \text{a click happened between } i-1 \text{ and } i$$

| Setting | Value | Meaning |
|---|---|---|
| `pause_gap_s` (τ) | 0.5 s | a pause longer than this starts a new stroke |
| `min_points` | 10 | shorter strokes are dropped as jitter |
| `min_length_px` | 0 | no minimum path length |

Each stroke is labelled **move** or **drag** (more than half its points with the button held). Moves and drags are
only compared with their own kind.

> **Note.** τ = 0.5 s is a *pause* threshold, so a stroke can last longer than 0.5 s. Cutting strokes to the first
> 0.5 s of each movement would match the short-signal scope exactly; this has not been run yet.

## 5. Normalization

So that strokes compare regardless of screen position, size and logging rate:

1. **Translation:** $q_i = p_i - p_1$, so every stroke starts at (0, 0).
2. **Scale:** divide by the bounding-box diagonal, so every stroke has size 1.
3. **Resampling:** redraw with $n = 64$ points evenly spaced along the path (arc length). This removes the
   difference between users logged every ~16 ms and every ~110 ms.

Optional for some methods: **rotation** so the stroke's end point lies on the +x axis (removes direction).

## 6. Profile (registration)

The profile of a user is the set of their normalized strokes from the **k registration sessions** (the user's
"library"). Tested k: 2–10 (DTW batch, up to 50 still running), 4 and 8 for the other methods.

## 7. Comparison methods

### 7.1 Banded DTW shape matching (main pipeline)

A new stroke $a$ matches the profile when some profile stroke $b$ of the same kind lies within the sensitivity:

$$D(i, j) = \lVert a_i - b_j \rVert + \min\{D(i-1, j-1),\, D(i-1, j),\, D(i, j-1)\}, \quad |i - j| \le w$$

$$\text{match} \iff \frac{D(n, n)}{n} \le \text{sensitivity}$$

| Setting | Value | Meaning |
|---|---|---|
| `dtw_band` | 0.1 → w = 6 points | how far DTW may stretch one stroke against the other |
| `sensitivity` | 0.02–1.00 (batch) | mean distance per point allowed for a match; lower is stricter |

### 7.2 Methods compared against DTW

Each was run on the same session draw (k = 4, seeds 945–949). Scripts were removed after the comparison and are in git
history.

| Method | Unit compared | Distance or rule |
|---|---|---|
| **Pure Euclidean** | stroke points | $d = \sqrt{\tfrac{1}{64}\sum_i \lVert q_i - p_i \rVert^2}$ to the nearest profile stroke; session score = median |
| **Geometric measures + Euclidean** | session | median per session of 7 measures (below), z-scored; Euclidean distance to the user's mean |
| **Convex hull** | stroke points | share of a session's stroke points inside the user's core hull (90% of points nearest the median path) |
| **Direction star** | session | median stroke in each of 8 directions; Euclidean distance between stars |
| **Density shape** | session | 32 × 32 grid of stroke points (direction and screen-relative size kept); Euclidean distance between √densities |

**The 7 geometric measures** (per stroke, after turning the chord onto the +x axis with length 1):

| Measure | Formula |
|---|---|
| Straightness | chord length / path length |
| Chord deviation | $\max_i \lvert y_i \rvert$ |
| Bow side | $\operatorname{mean}_i\, y_i$ (signed) |
| Mean Menger curvature | $\operatorname{mean}\, \kappa$, with $\kappa = \dfrac{4\,\text{Area}(p_{i-1}, p_i, p_{i+1})}{\lvert p_{i-1}p_i\rvert\,\lvert p_ip_{i+1}\rvert\,\lvert p_{i-1}p_{i+1}\rvert}$ |
| Peak Menger curvature | 90th percentile of $\kappa$ |
| Overshoot | $\max(\max_i x_i - 1,\; 0)$ |
| Hull fill | area of the stroke's own convex hull |

## 8. Decision rules

From strokes to a verdict on the user (DTW pipeline):

$$\text{session passes} \iff \frac{\text{matched strokes}}{\text{strokes}} \ge \texttt{match\_shape\_ratio} = 0.2$$

$$\text{user accepted} \iff \frac{\text{sessions passed}}{\text{sessions tested}} \ge \texttt{match\_session\_ratio} = 0.5$$

An impostor is tested against every legitimate profile and counts as through if **any** profile accepts them.
For the distance-based methods (7.2), a session is accepted when its distance is at most a threshold $t$, and $t$ is
set at the equal error point.

## 9. Evaluation

| Measure | Meaning | Goal |
|---|---|---|
| **FRR** (false rejection rate) | share of the user's own test sessions rejected | low |
| **FAR** (false acceptance rate) | share of impostor sessions accepted | low |
| **EER** (equal error rate) | the rate where FRR = FAR | low; 50% = chance |

- **Sweep (DTW):** 9 splits × sensitivity 0.02–1.00 (step 0.02) × 2–50 registration sessions, run by
  `17_batch.py` into `runs/efdc92/`; best setting = lowest mean of FRR and FAR over all splits.
- **Repeatability:** the other methods are run on 5 draws (seeds 945–949), reported as mean ± standard deviation.
- **Distinctiveness:** for each geometric measure, the share of its variation explained by the user
  (Kruskal–Wallis ε²).

## 10. Results so far

| Method | EER |
|---|---|
| DTW shape matching (best: sensitivity 0.04, 4 sessions) | ≈ 43% (FRR 42.8%, FAR 43.9%) |
| Geometric measures + Euclidean | 43.3 ± 5.0% |
| Convex hull (DTW filter 0.06, rotated) | 45.4 ± 1.1% |
| Pure Euclidean on stroke points | 45.4 ± 2.6% |
| Direction star | 49.5 ± 4.8% |
| Density shape (4 / 8 sessions) | 51.1 ± 6.4% / 50.0 ± 2.7% |

- **Best registration setting:** sensitivity 0.04 with 4 sessions. Stricter (0.02) rejects the user; looser
  (≥ 0.06) accepts almost every impostor; more sessions let more impostors match.
- **Distinctiveness:** the user explains only 0–3.4% of the variation of any geometric measure.
- **Answer so far:** short-stroke geometry carries only a faint personal trace; on its own it does not protect the
  legitimate user.

## 11. Limitations

- One dataset (Balabit) with 10 users.
- 2–10 registration sessions summarized (the 50-session sweep is still running).
- Strokes cut at 0.5 s pauses, not fixed 0.5 s pieces.
- Decisions per session; a sliding window of strokes (planned in Chapter 3, W = 30) is not yet evaluated.

## Scripts

| Step | Script (`experiment_earl/src/`) |
|---|---|
| Settings, data loading, session draw | `00_config.py` |
| User and session sampling | `01_sample_users.py`, `02_sample_sessions.py` |
| Segmentation and normalization | `03_chunk_shapes.py` |
| DTW matching | `04_match_shapes.py` |
| Sensitivity, sweep, plots | `05_sensitivity.py` … `08_run_notebook.py` |
| Matched shapes, genuine check, accuracy | `14_plot_matches.py`, `15_genuine_check.py`, `16_plot_accuracy.py` |
| Batch over splits × sensitivity × sessions | `17_batch.py` |
