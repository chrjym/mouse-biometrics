# Chapter 4

## RESULTS AND DISCUSSION

This chapter presents the results of each procedure described in Chapter 3, in the same order. Unless stated
otherwise, the results come from one random draw of users and session orders (seed 945), the same draw used in
Chapter 3 to select the best sensitivity and number of sessions. Splits are written as legitimate users × impostors,
as in Chapter 3: 1×5 means one legitimate user and five impostors.

### 4.1 Data Acquisition and Organization

The researchers successfully acquired and organized the Balabit Mouse Dynamic dataset as the main source of mouse data
for the study. The dataset contains mouse movement records from 10 users with a total of 1,676 sessions wherein it
provides the needed movement information to evaluate the behavioral patterns of individual users.

The dataset was organized based on the corresponding user and session, which allows the researchers to identify the
owner of each session and retrieve the mouse movement records needed for the next process. Of the 1,676 sessions, 405
are marked as illegal in the dataset's public labels, meaning that they were recorded by another person inside a
user's folder. These were excluded, leaving 1,271 sessions. Table 4.1 shows the number of sessions per user before and
after this step.

**Table 4.1.** Sessions per user

| User | Sessions in the dataset | Illegal sessions removed | Sessions used |
|---|---:|---:|---:|
| user7 | 158 | 37 | 121 |
| user9 | 130 | 43 | 87 |
| user12 | 240 | 49 | 191 |
| user15 | 253 | 70 | 183 |
| user16 | 201 | 38 | 163 |
| user20 | 114 | 20 | 94 |
| user21 | 121 | 22 | 99 |
| user23 | 142 | 33 | 109 |
| user29 | 124 | 20 | 104 |
| user35 | 193 | 73 | 120 |
| **Total** | **1,676** | **405** | **1,271** |

The number of usable sessions differs widely between users, from 87 (user9) to 191 (user12). Since every user must
supply the same number of sessions in a run, the smallest pool limits how many sessions can be used for a profile and
for testing.

The result of this process is an organized mouse movement dataset that contains the recorded sessions of the users,
which serves as the foundation for the preprocessing, segmentation, and shape-matching procedures.

### 4.2 Data Preprocessing and Segmentation

After cleaning, every session was divided into strokes using the 0.5-second pause and mouse-click rules, and strokes
with fewer than 10 points were discarded. This produced **109,948 strokes** from the 1,271 sessions, of which 106,320
(96.7 percent) are move strokes and 3,628 (3.3 percent) are drag strokes. Every stroke could be normalized, so all
109,948 strokes were used in the comparison. Table 4.2 summarizes the strokes of each user.

**Table 4.2.** Strokes per user after segmentation (medians are per stroke)

| User | Sessions | Strokes | Move | Drag | Median points | Median duration (s) | Median path length (px) | Median straightness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| user7 | 121 | 14,790 | 14,027 | 763 | 38 | 0.95 | 320 | 0.75 |
| user9 | 87 | 9,674 | 9,424 | 250 | 60 | 0.87 | 260 | 0.90 |
| user12 | 191 | 17,023 | 16,341 | 682 | 15 | 1.78 | 554 | 0.59 |
| user15 | 183 | 12,111 | 11,599 | 512 | 14 | 1.73 | 670 | 0.72 |
| user16 | 163 | 14,606 | 14,092 | 514 | 15 | 1.70 | 670 | 0.63 |
| user20 | 94 | 9,495 | 9,099 | 396 | 29 | 1.26 | 382 | 0.79 |
| user21 | 99 | 7,845 | 7,776 | 69 | 15 | 1.92 | 638 | 0.49 |
| user23 | 109 | 8,273 | 8,158 | 115 | 15 | 1.79 | 493 | 0.72 |
| user29 | 104 | 8,399 | 8,230 | 169 | 14 | 1.30 | 409 | 0.78 |
| user35 | 120 | 7,732 | 7,574 | 158 | 15 | 1.79 | 506 | 0.65 |
| **All** | **1,271** | **109,948** | **106,320** | **3,628** | **17** | **1.51** | **480** | **0.70** |

*Straightness* is the straight-line distance between a stroke's start and end divided by the length of its path; a
value of 1 is a perfectly straight stroke.

Two observations follow from Table 4.2. First, user7, user9 and user20 have two to four times as many points per
stroke as the other users. These are the three users whose sessions were logged about every 16 milliseconds instead of
every 110 milliseconds, so the raw number of points reflects the logging rate rather than the user's behavior. This
confirms the need to redraw every stroke with the same number of points (64) before comparison. Second, the median
stroke is fairly straight (0.70), and 26 percent of all strokes have a straightness of 0.9 or more. Near-straight
strokes look alike after normalization regardless of who drew them, which affects the shape-matching results below.

The result of this process is a set of normalized strokes, organized by session and movement type, that are ready for
shape matching.

### 4.3 Shape Matching using Dynamic Time Warping

To show how the matching rule behaves, Table 4.3 compares the strokes of legitimate and impostor test sessions against
the libraries described in Chapter 3, for three library sizes and several sensitivities. The values add up the four
splits. A legitimate session is compared with its own user's library; an impostor session is compared with the
library that accepts the most of that impostor's sessions.

**Table 4.3.** Share of strokes matched and share of sessions accepted (seed 945, all four splits)

| Sessions *k* | Sensitivity | Strokes matched: legitimate | Strokes matched: impostor | Sessions accepted: legitimate | Sessions accepted: impostor |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.02 | 1.7% | 1.0% | 0 / 11 | 0 / 11 |
| 1 | 0.05 | 16.7% | 15.2% | 5 / 11 | 0 / 11 |
| 1 | 0.10 | 41.0% | 37.4% | 9 / 11 | 9 / 11 |
| 1 | 0.20 | 75.5% | 74.7% | 11 / 11 | 11 / 11 |
| 5 | 0.02 | 6.2% | 4.3% | 0 / 55 | 0 / 55 |
| 5 | 0.05 | 45.6% | 34.5% | 52 / 55 | 49 / 55 |
| 5 | 0.10 | 78.3% | 67.6% | 55 / 55 | 55 / 55 |
| 25 | 0.01 | 5.8% | 4.0% | 2 / 275 | 2 / 275 |
| 25 | 0.02 | 29.4% | 26.4% | 183 / 275 | 147 / 275 |
| 25 | 0.05 | 69.1% | 65.1% | 275 / 275 | 273 / 275 |

At every setting, a legitimate user's strokes match their own library slightly more often than an impostor's strokes
do, but the gap is small, from about 1 to 11 percentage points. As the sensitivity or the library size grows, the
share of matched strokes rises for both groups at almost the same rate. Once it passes the 20 percent threshold, nearly
every session is accepted, legitimate or not. A larger library makes this happen at a lower sensitivity: with 25
sessions, 0.05 already accepts 273 of the 275 impostor sessions. The matched stroke pairs that were inspected were
mostly near-straight lines, which is consistent with the high straightness found in Table 4.2.

### 4.4 Selection of the Best Sensitivity and Number of Sessions

Table 4.4 shows the best setting found for each split, where each setting was scored as the average of the share of
legitimate users accepted and the share of impostors rejected (a score of 0.5 equals chance).

**Table 4.4.** Best sensitivity and number of sessions per split (seed 945)

| Split (L × I) | Best sensitivity | Sessions *k* | Legitimate users accepted | Impostors rejected | Legitimate sessions accepted | Impostor sessions accepted | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1×5 | 0.05 | 1 | 1 of 1 | 5 of 5 | 100% | 0% | 1.00 |
| 2×3 | 0.04 | 2 | 2 of 2 | 2 of 3 | 50% | 17% | 0.83 |
| 3×2 | 0.05 | 1 | 1 of 3 | 2 of 2 | 33% | 0% | 0.67 |
| 5×1 | 0.02 | 25 | 3 of 5 | 1 of 1 | 67% | 48% | 0.80 |

Every split scores above chance, but the results should be read with care. The settings with one or two sessions rest
on very few tested sessions: the 1×5 split at one session tests only one legitimate and five impostor sessions, so its
perfect score comes from six decisions. The only split whose best setting uses a large library (5×1, 25 sessions)
accepts 67 percent of the legitimate sessions but also 48 percent of the impostor's sessions. In addition, each best
setting was chosen on the same sessions that it was scored on, so these values are likely optimistic.

### 4.5 Experiments 1 and 2

To test the sensitivity and the number of sessions on all splits together, two further experiments were run on the
same draw. In Experiment 1, every user contributed one session, and the sensitivity was varied from 0.01 to 1.00. In
Experiment 2, the sensitivity was fixed at Experiment 1's best value, and the number of sessions was varied from 5 to
40 in steps of 5. Every tested session counts as one decision, with the impostor as the positive class: a true
positive (TP) is an impostor session rejected, a false negative (FN) an impostor session accepted, a true negative
(TN) a legitimate session accepted, and a false positive (FP) a legitimate session wrongly rejected. Accuracy is
(TP + TN) / (TP + TN + FP + FN). The best setting is the one with the highest accuracy over the four splits combined.

**Experiment 1.** The best sensitivity was **0.05**, with an accuracy of **0.727**: all 11 impostor sessions were
rejected, but 6 of the 11 legitimate sessions were rejected as well (Table 4.5).

**Table 4.5.** Experiment 1 at the best sensitivity (0.05, one session per user)

| Split (L × I) | TP | FP | FN | TN | Accuracy |
|---|---:|---:|---:|---:|---:|
| 1×5 | 5 | 0 | 0 | 1 | 1.00 |
| 2×3 | 3 | 1 | 0 | 1 | 0.80 |
| 3×2 | 2 | 2 | 0 | 1 | 0.60 |
| 5×1 | 1 | 3 | 0 | 2 | 0.50 |
| **All** | **11** | **6** | **0** | **5** | **0.727** |

Below 0.04, every session of both classes was rejected (accuracy 0.50). Above 0.05, impostor sessions started to be
accepted: at 0.06, 5 of the 11 impostor sessions passed, and at 0.10, 9 of 11 did.

**Experiment 2.** With the sensitivity fixed at 0.05, the best number of sessions was **5**, with an accuracy of only
**0.527** (Table 4.6). From 10 sessions upward, the accuracy stayed between 0.50 and 0.51, because almost every
session of both classes was accepted.

**Table 4.6.** Experiment 2 at the best number of sessions (sensitivity 0.05, five sessions per user)

| Split (L × I) | TP | FP | FN | TN | Accuracy |
|---|---:|---:|---:|---:|---:|
| 1×5 | 3 | 0 | 22 | 5 | 0.27 |
| 2×3 | 2 | 1 | 13 | 9 | 0.44 |
| 3×2 | 1 | 1 | 9 | 14 | 0.60 |
| 5×1 | 0 | 1 | 5 | 24 | 0.80 |
| **All** | **6** | **3** | **49** | **52** | **0.527** |

**Confusion matrices.** As planned with the adviser, the counts of each iteration were added to those of the
iterations before it, and the confusion matrix of each experiment is the total at the last iteration, all splits
combined. Table 4.7 therefore covers all 100 sensitivities of Experiment 1, and Table 4.8 all eight session counts of
Experiment 2.

**Table 4.7.** Confusion matrix of Experiment 1 (all sensitivities, all splits)

| | Actual: Impostor | Actual: Legitimate |
|---|---:|---:|
| **Rejected (Impostor)** | TP = 74 | FP = 71 |
| **Accepted (Legitimate)** | FN = 1,026 | TN = 1,029 |

**Table 4.8.** Confusion matrix of Experiment 2 (sensitivity 0.05, all session counts, all splits)

| | Actual: Impostor | Actual: Legitimate |
|---|---:|---:|
| **Rejected (Impostor)** | TP = 24 | FP = 6 |
| **Accepted (Legitimate)** | FN = 1,956 | TN = 1,974 |

In both matrices, most impostor sessions fall in the accepted row together with the legitimate sessions. Only 74 of
1,100 impostor sessions (6.7 percent) were rejected over the sensitivities of Experiment 1, and only 24 of 1,980
(1.2 percent) over the session counts of Experiment 2. Because these totals include every iteration, they describe the
whole range tested rather than the best setting alone.

### 4.6 Plot of the First Stroke of Each Session

Figure 4.1 shows the first stroke of each session after normalization, plotted from the origin (0, 0), for each user.
*(Figure 4.1 to be inserted.)*

### 4.7 Summary of Results

The results answer each procedure of Chapter 3 as follows:

1. **Data acquisition and organization.** The Balabit dataset gave 1,271 usable sessions from 10 users, after 405
   illegal sessions were removed (Table 4.1).
2. **Preprocessing and segmentation.** The sessions produced 109,948 strokes, almost all of them move strokes. The
   point counts confirm that the logging rate differs between users and must be removed by resampling, and a large
   share of strokes is close to a straight line (Table 4.2).
3. **Shape matching.** Legitimate strokes match their own library only slightly more often than impostor strokes
   match the most similar library. At any sensitivity or library size that accepts most legitimate sessions, most
   impostor sessions are accepted too (Table 4.3).
4. **Best sensitivity and sessions.** Every split has a setting above chance (Table 4.4), but these settings rely on
   few tested sessions and were chosen on the data they score. Across all splits, the best accuracy was 0.727 in
   Experiment 1 (sensitivity 0.05, one session) and 0.527 in Experiment 2 (five sessions), and the confusion matrices
   are dominated by impostor sessions that were accepted (Tables 4.5–4.8).

Other random draws give similar results: seed 946 reached its best at a sensitivity of 0.06 (accuracy 0.727) and
seed 989 at 0.01 (accuracy 0.50). Taken together, the initial results suggest that, at the settings tested, matching
the shapes of individual strokes does not reliably separate a legitimate user from an impostor. A likely reason is
that many strokes are near-straight lines, a shape every user produces. Further work is needed to find stroke
features that vary less within a user than between users.

---

# Appendix: Technical Reference, from Raw Mouse Data to the Confusion Matrix

This reference describes, step by step, how the experiment turns raw Balabit mouse logs into the confusion matrices of
Experiments 1 and 2. Every step follows the simulation notebook (`experiment_earl/notebooks/earl_simulation.ipynb`,
sections 1, 3 and 9); the parameter values are those of its `SETTINGS` and `EXPERIMENTS` blocks.

The pipeline has eight stages:

1. Load and clean each raw session file.
2. Assemble a session pool per user and draw the legitimate and impostor users.
3. Cut every session into strokes.
4. Normalize and resample every stroke.
5. Compare strokes with banded Dynamic Time Warping (DTW) and a sensitivity threshold.
6. Decide whether a whole session passes a user's library.
7. Count each tested session as TP, FP, FN or TN.
8. Add the counts over the iterations of each experiment to obtain the confusion matrix.

## A.1 Data Source and Cleaning

The experiment uses the Balabit Mouse Dynamics Challenge dataset, which contains ten users (`user7`, `user9`,
`user12`, `user15`, `user16`, `user20`, `user21`, `user23`, `user29`, `user35`). Balabit originally shipped a training
set and a test set; both are merged into one folder per user, so a session belongs to the user whose folder holds it.
The 405 test sessions that `public_labels.csv` marks `is_illegal = 1` were recorded by another person inside that
user's folder, and they are removed. This leaves 1,271 sessions, from 87 (`user9`) to 191 (`user12`) per user.

Each session file is a sequence of events with the columns `client timestamp`, `button`, `state`, `x` and `y`.
Loading a session applies four cleaning rules:

- Rows with a missing timestamp or coordinate are dropped.
- Scroll events (`button = Scroll`) are dropped, since they carry no pointer movement.
- Rows with `x = 65535` or `y = 65535` are dropped. These are logging glitches, not screen positions, and left in they
  would create jumps of about 60,000 px.
- Rows are put in time order with a *stable* sort on the client timestamp, because many Balabit timestamps tie and an
  unstable sort would reorder tied events. Time is then shifted so that the first event is at $t = 0$ s.

The result is a table of events $(t, x, y, \text{button}, \text{state})$ with
$\text{state} \in \{\text{Move}, \text{Drag}, \text{Pressed}, \text{Released}\}$.

## A.2 Session Pools and User Draw

Each user $u$ has a session pool $P_u$: all of the user's remaining sessions, shuffled once with a random generator
seeded by the string `"<seed>-<user>"`. The pool order is fixed for the whole run, so a library of $k+1$ sessions always
contains the library of $k$ sessions.

A run is defined by a split $(L, I)$, a sensitivity $s$ and a session count $k$. One random draw from the seed picks
$L$ legitimate users and then $I$ impostor users from the rest, with $L + I \le 10$. Experiments 1 and 2 use four
splits, written here as $L \times I$: $1 \times 5$, $5 \times 1$, $2 \times 3$ and $3 \times 2$. (The notebook's
`exp1.png` and `exp2.png` label the same splits the other way round, as $I \times L$.)

From the pool, three disjoint sets of sessions are taken:

| Set | Sessions | Role |
|---|---|---|
| Library $\mathcal{L}_u$ of legitimate user $u$ | first $k$ of $P_u$ | enrolled reference strokes |
| Legitimate test sessions of $u$ | last $k$ of $P_u$ | genuine attempts, never in the library |
| Impostor test sessions of impostor $v$ | first $k$ of $P_v$ | attack attempts |

Because the smallest pool has 87 sessions and the largest $k$ is 40, the first and last $k$ sessions of a legitimate
pool never overlap.

## A.3 Stroke Segmentation

A session is cut into *strokes* (also called chunks in the code), each a short continuous pointer movement.

1. Click events (`Pressed`, `Released`) are removed from the point sequence, but each one marks a boundary: the next
   point starts a new stroke.
2. A new stroke also starts whenever the time gap between two consecutive points exceeds $\tau = 0.5$ s.
3. A stroke with fewer than 10 recorded points is discarded as jitter. (A minimum path length can also be set; it is
   0 px, i.e. off, in this experiment.)
4. Each stroke is labelled **drag** if more than half of its points have `state = Drag`, and **move** otherwise.

A stroke is kept as the array of its points $(x_i, y_i, t_i)$. The number of strokes kept in this step is the
session's stroke count $n$, which is later used as the denominator of the session ratio (Section A.6).

## A.4 Stroke Normalization and Resampling

Users differ in screen size (1280×800 to 1920×1080) and logging rate (about 16 ms for `user7`, `user9` and `user20`,
about 110 ms for the rest). To compare the *shape* of a stroke rather than its position, size or sampling, each stroke
is normalized as follows:

1. **Translation.** The first point is moved to the origin: $\mathbf{p}_i' = \mathbf{p}_i - \mathbf{p}_1$.
2. **Scale.** The coordinates are divided by the diagonal of the stroke's bounding box,
   $d = \sqrt{(\max x' - \min x')^2 + (\max y' - \min y')^2}$, so every stroke has a bounding-box diagonal of 1.
3. **Resampling.** The stroke is redrawn with $N = 64$ points evenly spaced along its arc length by linear
   interpolation, so every stroke has the same number of points regardless of its duration or sampling rate.

If $d = 0$ or the arc length is 0 (the pointer did not move), the stroke cannot be normalized. It is left out of the
comparison but still counts in the session's stroke count $n$, so it can never be matched. (In the Balabit data, every
one of the 109,948 strokes could be normalized.)

Timing is not used after this step: the comparison is on the normalized 2-D shape only.

## A.5 Stroke Comparison: Banded DTW and Sensitivity

Two normalized strokes $\mathbf{a} = (\mathbf{a}_1, \dots, \mathbf{a}_N)$ and
$\mathbf{b} = (\mathbf{b}_1, \dots, \mathbf{b}_N)$ are compared with Dynamic Time Warping. With
$c(i, j) = \lVert \mathbf{a}_i - \mathbf{b}_j \rVert_2$ the Euclidean distance between two points, the cumulative cost is

$$
D(i, j) = c(i, j) + \min\{D(i-1, j),\; D(i, j-1),\; D(i-1, j-1)\}, \qquad D(0, 0) = 0,
$$

and the DTW cost of the pair is $\text{DTW}(\mathbf{a}, \mathbf{b}) = D(N, N)$. A Sakoe–Chiba band restricts the
warping to $|i - j| \le w$, where $w = \operatorname{round}(0.1 \cdot N) = 6$ points, so one stroke can be stretched
against the other by at most 10% of its length.

Only strokes of the same kind are compared: a move stroke against move strokes, a drag stroke against drag strokes. For
a query stroke $\mathbf{q}$ and a library $\mathcal{L}$, the stroke's best cost is the smallest DTW cost to any library
stroke of its kind:

$$
D^*(\mathbf{q}, \mathcal{L}) = \min_{\mathbf{b} \in \mathcal{L},\ \text{kind}(\mathbf{b}) = \text{kind}(\mathbf{q})}
\text{DTW}(\mathbf{q}, \mathbf{b}).
$$

The stroke **matches** the library when

$$
D^*(\mathbf{q}, \mathcal{L}) \le s \cdot N,
$$

where $s$ is the **sensitivity**. Dividing both sides by $N$, the rule reads: the mean distance per point is at most
$s$, in units of the bounding-box diagonal. A lower $s$ is stricter. Since $D^*$ does not depend on $s$, it is computed
once per pair of sessions and reused for every sensitivity (`cache/costs_<seed>.pkl`).

## A.6 Session Decision

Let a test session $S$ have stroke count $n_S$, and let $m_S$ be the number of its strokes that match the library
$\mathcal{L}$. The session's match ratio is

$$
r(S, \mathcal{L}) = \frac{m_S}{\max(n_S, 1)},
$$

and the session **passes** (is accepted as the library's owner) when

$$
r(S, \mathcal{L}) \ge \rho, \qquad \rho = 0.2.
$$

That is, a session is accepted when at least 20% of its strokes have a close shape somewhere in the library.

**Which library an impostor faces.** A legitimate user's test sessions are scored against that user's own library.
An impostor's $k$ test sessions are scored against every legitimate library of the split, and the library that passes
the most of them is used (ties: the library with the higher share of matched strokes). This models the strongest
attacker in the split: the impostor is assigned to the legitimate user they resemble most.

## A.7 From Sessions to Confusion Counts

Every tested session is one authentication decision. The **positive class is the impostor**: a positive decision
means the session is rejected as an impostor. For one run, the four counts are

| Count | Actual user | Decision | Computed as |
|---|---|---|---|
| TP | impostor | rejected (impostor caught) | impostor sessions that do **not** pass |
| FN | impostor | accepted (impostor let in) | impostor sessions that pass |
| TN | legitimate | accepted (real user accepted) | legitimate sessions that pass |
| FP | legitimate | rejected (user wrongly blocked) | legitimate sessions that do **not** pass |

A run of split $(L, I)$ with $k$ sessions tests $L \cdot k$ legitimate and $I \cdot k$ impostor sessions, so
$TN + FP = L k$ and $TP + FN = I k$. Its accuracy is

$$
\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}.
$$

The confusion matrix is laid out with the decision as rows and the actual user as columns:

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Decision: Impostor (rejected)** | TP | FP |
| **Decision: Legitimate (accepted)** | FN | TN |

(The notebook also records whether a *user* goes through, i.e. at least 50% of their sessions pass. That user-level
flag is used by the best-per-split selection of Section 4.4, not by the confusion matrices, which count sessions.)

## A.8 Experiments 1 and 2

Each *point* of an experiment is one run for every split, i.e. one $(s, k)$ setting tested on the four splits.

**Experiment 1 (User × User × Sensitivity).** The session count is fixed at $k = 1$ and the sensitivity takes every
value $s = 0.01, 0.02, \dots, 1.00$ (100 points). With $k = 1$, each point tests
$1 + 2 + 3 + 5 = 11$ legitimate sessions and $5 + 3 + 2 + 1 = 11$ impostor sessions over the four splits.

**Experiment 2 (User × Sensitivity × Session).** The sensitivity is fixed at Experiment 1's best value $s^*$ and the
session count takes $k = 5, 10, \dots, 40$ (8 points). Each point tests $11k$ legitimate and $11k$ impostor sessions.

The processing of each experiment is:

1. **Counts per point and split.** Run the procedure of Sections A.2–A.7 and record TP, FP, FN and TN.
2. **Running totals.** Within each split, the counts of every point are added to those of the points before it (in
   increasing $s$ or $k$). For split $j$ at point $p$:
   $$
   TP^{\text{tot}}_{j,p} = \sum_{p' \le p} TP_{j,p'}, \quad \text{and likewise for } FP, FN, TN.
   $$
3. **Graphs.** Two graphs plot the running totals per split, one line per split:
   legitimate accuracy $= TN^{\text{tot}} / (TN^{\text{tot}} + FP^{\text{tot}})$ and
   impostor accuracy $= TP^{\text{tot}} / (TP^{\text{tot}} + FN^{\text{tot}})$.
4. **Best point.** For each point, the counts of the four splits are added (the point's own counts, not the running
   totals) and its accuracy is computed. The point with the highest accuracy is the best; ties go to the lower
   sensitivity or the fewer sessions. Experiment 1's best sensitivity $s^*$ becomes the fixed sensitivity of
   Experiment 2.
5. **Confusion matrix.** The experiment's confusion matrix is the running total at the **last** point, added over the
   four splits. In Experiment 1 it therefore covers all 100 sensitivities ($100 \times 11 = 1{,}100$ sessions in each
   column); in Experiment 2 it covers all eight session counts ($11 \times (5 + 10 + \dots + 40) = 1{,}980$ sessions in
   each column). It summarizes the whole sweep, not the best point alone.

The outputs are written to `runs/<hash>/experiments/`: `exp{1,2}_points.csv` (counts and running totals per point and
split), `exp{1,2}_overall.csv` (counts and accuracy per point, all splits, with the `best` flag),
`exp{1,2}_confusion.csv` and the figures `exp1.png` and `exp2.png`.

## A.9 Sources of the Results

| Result | Seed | Source |
|---|---|---|
| Tables 4.1, 4.2 (sessions, strokes) | any (counts do not depend on the seed) | dataset folders, `runs/a6e6f7/strokes/all_strokes.csv` |
| Table 4.3 (strokes matched, sessions accepted) | 945 | `runs/19399f/accuracy.csv` |
| Table 4.4 (best per split) | 945 | `runs/19399f/best/best.csv` |
| Tables 4.5–4.8 (Experiments 1 and 2) | 945 | `runs/19399f/experiments/` |
| Other seeds | 946, 989 | `runs/a6e6f7/experiments/`, `runs/b54011/experiments/` |

## A.10 Summary of Parameters

| Symbol | Setting | Value | Stage |
|---|---|---|---|
| — | `labels_file` | sessions with `is_illegal = 1` dropped | A.1 |
| — | `seed` | 945 (also 946, 989) | A.2 |
| $(L, I)$ | `splits` | (1, 5), (2, 3), (3, 2), (5, 1) | A.2 |
| $\tau$ | `pause_gap_s` | 0.5 s | A.3 |
| — | `min_points` | 10 | A.3 |
| — | `min_length_px` | 0 (off) | A.3 |
| $N$ | `resample_n` | 64 | A.4 |
| $w$ | `dtw_band` | $0.1 \cdot N$ = 6 points | A.5 |
| $s$ | `sensitivity` | 0.01–1.00 (Exp. 1); $s^*$ (Exp. 2) | A.5 |
| $\rho$ | `match_shape_ratio` | 0.2 | A.6 |
| $k$ | `sessions_per_user` | 1 (Exp. 1); 5–40 (Exp. 2) | A.2, A.8 |
