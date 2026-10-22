# Chapter 3: Methodology

> Draft, 2026-10-23. Describes the EARL shape-matching pipeline in `experiment_earl/` as it stands now (DTW only; One-Class SVM and hull models removed 2026-10-14). Parameter values are the committed defaults in `experiment_earl/config.yaml` and `experiment_earl/sweep.yaml`. Items marked **[CITATION NEEDED]** have no verified entry in `paper/references/` yet. The objectives in Section 3.1 are written from the thesis title and the adviser log; align their wording with Chapter 1 before submission.

## 3.1 Objectives and Research Design

The study asks whether short mouse strokes carry a geometric "behavioral fingerprint" strong enough to tell one user from another for continuous authentication. It follows a quantitative, experimental design built as a machine-learning pipeline: raw mouse logs are organized, cleaned and labelled; short regions of interest (strokes) are detected; each stroke is turned into a normalized shape; users are enrolled as libraries of these shapes; and new sessions are scored against them.

**General objective.** To measure how well the geometric shape of short mouse trajectories identifies users for continuous authentication.

**Specific objectives.**

1. To acquire and organize a mouse-dynamics dataset into per-user session pools that support reproducible enrollment and testing.
2. To preprocess and label the raw event streams so that only valid cursor paths, owned by a known user, enter the model.
3. To detect short regions of interest (strokes, ≈ 0.5 s scale) in continuous mouse movement as the unit of a user's mannerism.
4. To extract position-, size- and speed-invariant geometric features from each stroke.
5. To evaluate and compare model configurations (sensitivity, enrollment size, legitimate/impostor mixes, seeds) using accuracy, FAR, FRR and EER.

**Table 3.1.** Objectives mapped to methodology sections and outputs.

| Objective | Section | Script(s) | Output |
|---|---|---|---|
| 1. Data acquisition and organization | 3.2 | `00_config.session_pool`, `01_sample_users`, `02_sample_sessions` | Seeded per-user session pools; legitimate/impostor draw |
| 2. Preprocessing and labelling | 3.3 | `03_chunk_shapes` (loader) | Clean, time-ordered events with owner label |
| 3. ROI detection | 3.4 | `03_chunk_shapes` | Move/drag strokes per session |
| 4. Feature extraction | 3.5 | `03_chunk_shapes`, `04_match_shapes` | 64-point normalized shapes; DTW distances |
| 5. Performance evaluation | 3.6 | `05_sensitivity`, `10`, `12`, `14`, `16`, `17` | Accuracy, FAR, FRR, EER; comparison tables and heatmaps |

All settings live in one configuration file and every random choice is seeded, so the same configuration reproduces the same users, sessions and results.

## 3.2 Data Acquisition and Organization (Objective 1)

### 3.2.1 Procedure

1. **Acquire** the public Balabit Mouse Dynamics Challenge dataset **[CITATION NEEDED: Balabit dataset]**. It records 10 users (user7, user9, user12, user15, user16, user20, user21, user23, user29, user35) during remote-desktop work.
2. **Merge** Balabit's `training_files` (65 sessions) and `test_files` (1,611 sessions) into one folder per user, `datasets/balabit/users/<user>/` (adviser, 2026-10-14). This yields 1,676 sessions, 114–253 per user.
3. **Assign ownership** by folder: a session belongs to the user whose folder holds it (adviser and group, 2026-10-08). The public label file is not used.
4. **Shuffle** each user's pool once with a generator seeded by `"{seed}-{user}"`. The order is fixed for the whole run.
5. **Draw roles.** One seeded draw selects $N_L$ legitimate users and $N_I$ impostor users ($N_L + N_I \le 10$).
6. **Partition sessions.** A legitimate user's *first* $s$ pool sessions form the enrollment library; their *last* sessions (never in the library) are the genuine test set. An impostor contributes their first $s$ sessions as attack attempts.

SapiMouse (120 users) is kept in the repository as a supplementary benchmark but is not used in the reported runs.

### 3.2.2 Parameters

**Table 3.2.** Data organization parameters.

| Parameter | Config key | Default | Meaning |
|---|---|---|---|
| Seed | `seed` | 945 (sweep: 927) | Fixes users, roles and session order |
| Legitimate users | `n_legitimate` | 1 | Users with an enrolled profile |
| Impostor users | `n_impostor` | 9 | Users attacking the profiles |
| Sessions per user | `sessions_per_user` | 2 | Library size $s$ (sweep: 1–40) |
| Data folder | `dataset_dir` | `datasets/balabit/users` | Merged per-user folders |

### 3.2.3 Data organization output

Each run is written to `runs/<hash>/<N_L>_<N_I>_<sensitivity>_<s>/`, where the hash covers every other setting. A config snapshot and `run.json` are stored with the results, so no run overwrites another.

## 3.3 Data Preprocessing and Labelling (Objective 2)

### 3.3.1 Procedure

Each session file (columns `record timestamp, client timestamp, button, state, x, y`; times in seconds) is loaded as follows:

1. Drop rows with missing time or position.
2. Drop scroll events (no cursor path).
3. Drop rows with $x = 65535$ or $y = 65535$; these are logging glitches that otherwise create jumps of about 60,000 px.
4. Order rows by client timestamp with a **stable** sort, because Balabit timestamps tie often (~0.1 s record resolution) and an unstable sort would reorder the path.
5. Shift time so each session starts at $t = 0$.

### 3.3.2 Labelling

Two labels are attached, both without manual annotation:

- **Identity label:** the owner user ID from the folder (Section 3.2.1, step 3), and its role in the draw — *legitimate* or *impostor*.
- **Event label:** the Balabit `state` field (`Move`, `Drag`, `Pressed`, `Released`). Click states mark ROI boundaries (Section 3.4); `Move`/`Drag` decides the stroke kind.

A session is then labelled *genuine* when it is a legitimate user's held-out session scored against that user's own library, and *impostor* when it comes from an impostor user. These labels define the ground truth for Section 3.6.

### 3.3.3 Known biases

Users 7, 9 and 20 log every ~16 ms; the others every ~110 ms. Screens range from 1280×800 (user23) to 1920×1080 (users 15, 16). Features that depend on point count or absolute size would partly measure the hardware. The normalization in Section 3.5 removes both effects from the shape.

## 3.4 Regions of Interest (ROI) Detection (Objective 3)

### 3.4.1 Method

In this study, a region of interest is a **stroke**: one continuous burst of cursor movement between pauses or clicks. This is the operational answer to the adviser's request (2026-08-31) to compare *short* mouse signals that carry a user's mannerisms. ROIs are detected by rule-based temporal segmentation, not by a learned detector.

### 3.4.2 Procedure

1. **Pause boundary.** Start a new stroke when the gap between consecutive events exceeds $g$:
   $$t_k - t_{k-1} > g,\qquad g = 0.5\ \text{s}.$$
2. **Click boundary.** Every `Pressed` or `Released` event also starts a new stroke; click rows are not part of any path.
3. **Point filter.** Discard strokes with fewer than $m_{\min} = 10$ points as jitter.
4. **Length filter.** Discard strokes whose path is shorter than `min_length_px` (0 = off).
5. **Kind label.** Label a stroke *drag* when more than half its points are `Drag`, else *move*. Moves and drags are only ever compared with their own kind.

### 3.4.3 Parameters

**Table 3.3.** ROI detection parameters.

| Symbol | Config key | Default | Meaning |
|---|---|---|---|
| $g$ | `pause_gap_s` | 0.5 s | Pause that ends a stroke |
| $m_{\min}$ | `min_points` | 10 | Minimum recorded points per stroke |
| $\ell_{\min}$ | `min_length_px` | 0 px | Minimum path length (0 = no filter) |
| — | (fixed) | click | Click events always split strokes |

## 3.5 Feature Extraction (Objective 4)

### 3.5.1 Procedure

Each stroke $C = (\mathbf{p}_1, \dots, \mathbf{p}_m)$ is turned into a fixed-length geometric shape vector:

1. **Translation.** $\mathbf{q}_i = \mathbf{p}_i - \mathbf{p}_1$, so every stroke starts at the origin.
2. **Scale normalization.** Divide by the bounding-box diagonal
   $d = \sqrt{(\max q_x - \min q_x)^2 + (\max q_y - \min q_y)^2}$, so every stroke has diagonal 1. This removes absolute size and most of the screen-resolution effect.
3. **Arc-length resampling.** With cumulative length $\ell_i = \sum_{j=2}^{i}\lVert\mathbf{q}_j-\mathbf{q}_{j-1}\rVert$, interpolate $n = 64$ points evenly spaced on $[0, \ell_m]$. This removes speed and logging rate, leaving pure shape.
4. **Degenerate strokes.** Strokes with $d = 0$ or $\ell_m = 0$ cannot be normalized; they are excluded from matching but still counted in session denominators.

The feature of a stroke is therefore the $64 \times 2$ point sequence $\mathbf{a} \in \mathbb{R}^{64\times 2}$, a position-, size- and speed-invariant description of its geometry.

### 3.5.2 Similarity feature: banded DTW

Two shapes $\mathbf{a}, \mathbf{b}$ are compared with banded Dynamic Time Warping:

$$D(i,j) = \lVert\mathbf{a}_i-\mathbf{b}_j\rVert_2 + \min\{D(i-1,j-1),\,D(i-1,j),\,D(i,j-1)\},$$

with cells outside $|i-j| \le w$, $w = \operatorname{round}(\beta n) = 6$, set to infinity **[CITATION NEEDED: Sakoe–Chiba band]**. The band keeps the start of one stroke from aligning with the end of the other. The per-point cost $D(n,n)/n$ is the similarity feature used for decisions.

### 3.5.3 Model configuration (enrollment and matching)

- **Enrollment.** A user's profile is the library $\mathcal{L}_u$ of normalized shapes from their first $s$ sessions, split by kind.
- **Stroke decision.** A stroke matches $\mathcal{L}_u$ when some library shape of the same kind satisfies $D(n,n) \le \tau n$, where $\tau$ is the **sensitivity**. Computation stops early once every cell of a row exceeds $\tau n$.
- **Session decision.** With $|S|$ strokes, the session match ratio is $r(S,u) = |\{C\in S: C \text{ matches } \mathcal{L}_u\}| / |S|$; the session is accepted when $r(S,u) \ge \rho_s$.
- **User decision.** A user is accepted by a profile when at least $\rho_u$ of their sessions are accepted. An impostor is scored against the legitimate profile that accepts most of their sessions.

**Table 3.4.** Feature extraction and model configuration.

| Symbol | Config key | Default | Meaning |
|---|---|---|---|
| $n$ | `resample_n` | 64 | Points per normalized stroke |
| $\beta$ | `dtw_band` | 0.1 | DTW band as a share of $n$ |
| $\tau$ | `sensitivity` | 0.06 (sweep 0.01–1.00) | Max mean DTW cost per point for a match |
| $\rho_s$ | `match_shape_ratio` | 0.2 | Share of strokes for a session to pass |
| $\rho_u$ | `match_session_ratio` | 0.5 | Share of sessions for a user to pass |

DTW is implemented with Numba (parallel), and pair distances are cached in `experiment_earl/cache/` keyed by the chunking, band and resampling settings, so a sensitivity sweep only re-thresholds saved distances.

## 3.6 Performance Evaluation and Comparison (Objective 5)

### 3.6.1 Metrics

For genuine sessions $G$ and impostor sessions $M$:

$$\text{FRR} = \frac{|\{g\in G: g \text{ rejected}\}|}{|G|},\qquad \text{FAR} = \frac{|\{h\in M: h \text{ accepted}\}|}{|M|}.$$

- **EER**: the error where FAR = FRR, found by scanning every observed session score as a cut $c$, taking $c^*$ that minimizes $|\text{FRR}-\text{FAR}|$, and reporting their mean.
- **User accuracy** (group rule, 2026-10-14):
  $$\text{Acc} = \tfrac{1}{2}\left(\frac{\text{legitimate accepted}}{N_L} + \frac{\text{impostors rejected}}{N_I}\right),$$
  where 1 is perfect and 0.5 is chance (equal to accepting or rejecting everyone).
- **Confusion matrix** per split, sensitivity and session count (TP = genuine accepted, FN = genuine rejected, FP = impostor accepted, TN = impostor rejected).

### 3.6.2 Comparison procedure

Configurations are compared in four studies, each holding all other settings fixed:

1. **Sensitivity study (user × user × sensitivity).** Sweep $\tau$ from 0.01 to 1.00 in 0.01 steps (`16_sweep_sensitivity.py`). Plot accuracy and FAR/FRR against $\tau$ to find where users begin to separate.
2. **Enrollment-size study (user × session × sensitivity).** Vary library size $s$ from 1 to 40 sessions at each $\tau$; heatmaps of accuracy over ($\tau$, $s$) (`17_plot_sweep.py`, `10_plot_accuracy.py`).
3. **Legitimate/impostor mix study.** Repeat 1–2 for the splits $[N_L, N_I] \in \{[5,1], [1,5], [3,2], [2,3]\}$ to see whether results depend on how many profiles an impostor can try.
4. **Generalization (seed) check.** The best ($\tau$, $s$) per split is chosen on one seed (`12_pick_best.py`) and applied unchanged to new seeds (`14_seed_check.py`). The drop from the tuning seed to new seeds measures over-fitting to the draw.

**Table 3.5.** Comparison matrix.

| Factor compared | Levels | Held fixed | Reported |
|---|---|---|---|
| Sensitivity $\tau$ | 0.01–1.00 (100 values) | $s$, split, seed | Accuracy, FAR, FRR vs $\tau$ |
| Sessions per user $s$ | 1–40 | $\tau$, split, seed | Accuracy heatmap ($\tau \times s$) |
| Split $[N_L, N_I]$ | 5×1, 1×5, 3×2, 2×3 | $\tau$, $s$, seed | Best accuracy and EER per split |
| Seed | tuning seed vs 3 new seeds | chosen $\tau$, $s$ | Accuracy and EER drop |

### 3.6.3 Baseline and interpretation

Results are judged against the chance line (accuracy 0.5, EER 0.5). A configuration is considered discriminative only if it beats chance on seeds it was not tuned on. Because sensitivity and session count are selected on the same draw that is scored, the tuning-seed numbers are reported as upper bounds and the seed-check numbers as the honest estimate.

## 3.7 Implementation

Python 3.11 with NumPy and pandas (data), Numba (banded DTW), scikit-learn (metrics), Matplotlib (figures) and PyYAML (configuration). Scripts are numbered by stage: `01`–`02` sampling, `03` preprocessing/ROI/normalization, `04` matching, `05` sensitivity for one draw, `10`/`12`/`14`/`16`/`17` evaluation and comparison. **[TO FILL: hardware used for the reported runs.]**

## 3.8 Limitations

- **Small population.** Ten Balabit users cap $N_L + N_I \le 10$.
- **Ownership assumption.** Merged test sessions are assigned to their folder owner, though Balabit's labels mark about half of the labelled ones as impostors.
- **Parameter selection on evaluated data**, mitigated only by the seed check.
- **Divergence from the proposal.** Closed-form descriptors (chord deviation, Menger curvature, straightness), convex hull bounding, discrete Fréchet distance and a dynamic trust threshold are not implemented; DTW and fixed ratio rules are used instead.
