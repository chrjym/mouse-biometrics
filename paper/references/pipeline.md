# Methodology

How this study was conducted, from raw mouse logs to a verdict on the user, written so that others can trust and
replicate it. It describes the pipeline as implemented and tested in `experiment_earl/` up to 2026-10-18, not the
original proposal. Results are summarized in
[`experiment_earl/shape_results/README.md`](../../experiment_earl/shape_results/README.md).

**Aim.** Find out whether the geometric shape of a user's short mouse movements is personal enough to tell them
apart from other users, and so protect the legitimate user through continuous authentication.

---

## 1. Research design

- **Quantitative:** every result is a measured number (distances, error rates), not an opinion or interview.
- **Experimental:** the study changes settings on purpose (sensitivity, number of registration sessions, comparison
  method) and measures what happens to the error rates.
- **Comparative:** six shape-comparison methods are run on the same data and the same session draw, so they can be
  compared like for like.
- **Scope:** geometry (shape) is the main point; short signals (a user's mannerism within a short stroke, target
  ≈ 0.5 s); explainable, closed-form measures only (no black-box models).

**Research questions**

1. Is a user's short-stroke geometry distinct from other users'?
2. Which sensitivity and how many registration sessions give the best profile?
3. Does the profile protect the legitimate user: accept them while rejecting impostors?

---

## 2. Participants / sample

No people were recruited. The study uses an existing public dataset of recorded mouse behavior.

| Item | Value |
|---|---|
| Dataset | Balabit Mouse Dynamics Challenge |
| Users | 10 (`user7, 9, 12, 15, 16, 20, 21, 23, 29, 35`) |
| Sessions per user | 114–253 (training and test files merged per user) |
| Labels | a session belongs to the user whose folder it is in; `public_labels.csv` is not used |
| Unit of analysis | a **stroke** (one short movement), grouped into **sessions** |

**Sampling of sessions.** One random draw from a fixed seed (945; repeated draws use 945–949) shuffles each user's
sessions once with `Random(f"{seed}-{user}")`:

| Role | Sessions used | Purpose |
|---|---|---|
| **Profile (registration)** | first k of the user's shuffled list | build the user's profile |
| **Own test** | last k of the user's list (never in a profile) | should be **accepted** |
| **Impostor test** | other users' sessions (never in this profile) | should be **rejected** |

Users are split into `n_legitimate` legitimate and `n_impostor` impostor users
(`n_legitimate + n_impostor = 10`); the batch tests all 9 splits (1/9 … 9/1).

---

## 3. Materials and tools

| Kind | What |
|---|---|
| Data | Balabit raw session logs: `client timestamp` (s), `button`, `state` (Move, Drag, Pressed, Released), `x`, `y` (screen pixels, y grows downward) |
| Language | Python 3 (project virtual environment `.venv`) |
| Libraries | NumPy, pandas, SciPy (convex hull, statistics), Numba (fast DTW), Matplotlib (figures), PyYAML (settings), Jupyter (notebook) |
| Settings | `experiment_earl/config.yaml` (every value below), `experiment_earl/batch.yaml` (sweep grid) |
| Code | numbered scripts in `experiment_earl/src/` (see the script map at the end) |
| Output | one folder per configuration under `experiment_earl/runs/`, with a copy of its settings |

---

## 4. Procedure

```
 1. Cleaning        drop scroll and glitch rows, stable time sort
        │
 2. Session draw    seeded shuffle per user → profile | own test | impostor test
        │
 3. Segmentation    cut each session into short strokes at pauses and clicks
        │
 4. Normalization   start at (0, 0), scale to size 1, 64 points evenly spaced along the path
        │
 5. Profile         the user's strokes from k registration sessions
        │
 6. Comparison      new stroke vs profile: DTW / Euclidean / convex hull / geometric measures
        │
 7. Decision        stroke matches → session passes → user accepted or rejected
```

### Step 1. Cleaning

- Drop rows with missing time or position, scroll rows (no path), and glitch rows where x or y is 65535.
- Sort by time with a **stable** sort, because many timestamps tie, then set the first event to t = 0.

### Step 2. Session draw

As described in Section 2: profile = first k sessions, own test = last k, impostor test = other users' sessions.

### Step 3. Segmentation into short strokes

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

### Step 4. Normalization

So that strokes compare regardless of screen position, size and logging rate:

1. **Translation:** $q_i = p_i - p_1$, so every stroke starts at (0, 0).
2. **Scale:** divide by the bounding-box diagonal, so every stroke has size 1.
3. **Resampling:** redraw with $n = 64$ points evenly spaced along the path (arc length). This removes the
   difference between users logged every ~16 ms and every ~110 ms.

Optional for some methods: **rotation** so the stroke's end point lies on the +x axis (removes direction).

### Step 5. Profile (registration)

The profile of a user is the set of their normalized strokes from the **k registration sessions** (the user's
"library"). Tested k: 2–10 (DTW batch; up to 50 still running), 4 and 8 for the other methods.

### Step 6. Comparison

**6a. Banded DTW shape matching (main pipeline).** A new stroke $a$ matches the profile when some profile stroke $b$
of the same kind lies within the sensitivity:

$$D(i, j) = \lVert a_i - b_j \rVert + \min\{D(i-1, j-1),\, D(i-1, j),\, D(i, j-1)\}, \quad |i - j| \le w$$

$$\text{match} \iff \frac{D(n, n)}{n} \le \text{sensitivity}$$

| Setting | Value | Meaning |
|---|---|---|
| `dtw_band` | 0.1 → w = 6 points | how far DTW may stretch one stroke against the other |
| `sensitivity` | 0.02–1.00 (batch) | mean distance per point allowed for a match; lower is stricter |

**6b. Methods compared against DTW.** Each was run on the same session draw (k = 4, seeds 945–949). The scripts were
removed after the comparison and are in git history.

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

### Step 7. Decision

From strokes to a verdict on the user (DTW pipeline):

$$\text{session passes} \iff \frac{\text{matched strokes}}{\text{strokes}} \ge \texttt{match\_shape\_ratio} = 0.2$$

$$\text{user accepted} \iff \frac{\text{sessions passed}}{\text{sessions tested}} \ge \texttt{match\_session\_ratio} = 0.5$$

An impostor is tested against every legitimate profile and counts as through if **any** profile accepts them.
For the distance-based methods (6b), a session is accepted when its distance is at most a threshold $t$, set at the
equal error point.

---

## 5. Analysis methods

| Measure | Meaning | Goal |
|---|---|---|
| **FRR** (false rejection rate) | share of the user's own test sessions rejected | low |
| **FAR** (false acceptance rate) | share of impostor sessions accepted | low |
| **EER** (equal error rate) | the rate where FRR = FAR | low; 50% = chance |

- **Choosing the best setting (DTW):** 9 splits × sensitivity 0.02–1.00 (step 0.02) × 2–50 registration sessions,
  run by `17_batch.py` into `runs/efdc92/`; best setting = lowest mean of FRR and FAR, totalled over all splits.
- **Comparing methods:** EER of each method on the same draw, repeated over 5 draws (seeds 945–949) and reported as
  mean ± standard deviation, so one lucky draw cannot decide the result.
- **Distinctiveness:** for each geometric measure, the share of its variation explained by the user
  (Kruskal–Wallis ε²). Near 0 means users are not distinct on that measure.
- **Visual checks:** figures of each user's profile against their own and other users' sessions
  (`experiment_earl/shape_results/`).

### Results so far

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

### Limitations

- One dataset (Balabit) with 10 users.
- 2–10 registration sessions summarized (the 50-session sweep is still running).
- Strokes cut at 0.5 s pauses, not fixed 0.5 s pieces.
- Decisions per session; a sliding window of strokes (planned in Chapter 3, W = 30) is not yet evaluated.

---

## Script map

| Procedure step | Script (`experiment_earl/src/`) |
|---|---|
| Settings, cleaning, session draw | `00_config.py` |
| User and session sampling | `01_sample_users.py`, `02_sample_sessions.py` |
| Segmentation and normalization | `03_chunk_shapes.py` |
| DTW comparison and decision | `04_match_shapes.py`, `05_sensitivity.py` |
| Sweep, plots, notebook | `06_sweep.py`, `07_plot_shapes.py`, `08_run_notebook.py` |
| Matched shapes, genuine check, accuracy | `14_plot_matches.py`, `15_genuine_check.py`, `16_plot_accuracy.py` |
| Batch over splits × sensitivity × sessions | `17_batch.py` |
