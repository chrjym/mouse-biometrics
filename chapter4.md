# Chapter 4

## INITIAL RESULTS

### Data Acquisition and Organization

The researchers successfully acquired and organized the Balabit Mouse Dynamic dataset as the main source of mouse data
for the study. The dataset contains mouse movement records from 10 users with a total of 1,676 sessions wherein it
provides the needed movement information to evaluate the behavioral patterns of individual users.

The dataset was organized based on the corresponding user and session, which allows the researchers to identify the
owner of each session and retrieve the mouse movement records needed for the next process.

The result of this process is an organized mouse movement dataset that contains the recorded sessions of the users,
which serves as the foundation for the preprocessing, segmentation, and geometric feature extraction procedures.

### Data Preprocessing and Segmentation

Before segmentation, the researchers cleaned each session file to remove records that do not represent actual cursor
movement. Scroll events were removed because they do not change the cursor position. Records with x or y coordinates
of 65,535 were also removed, since these are logging errors in the dataset rather than screen positions; keeping them
would create false jumps of about 60,000 pixels. The remaining records were arranged in time order using the client
timestamp. A stable sort was used so that records sharing the same timestamp keep their recorded order. The
researchers also excluded the 405 sessions that the dataset's public labels mark as illegal. These sessions were
recorded by another person inside a user's folder and would misrepresent that user's behavior. This left 1,271
sessions, from 87 to 191 per user.

Each cleaned session was then divided into strokes, where a stroke is one short, continuous movement of the cursor. A
new stroke begins after every mouse click, or whenever the pause between two consecutive records is longer than 0.5
seconds. Strokes with fewer than 10 recorded points were discarded as jitter. Each remaining stroke was labelled a move
stroke or a drag stroke, depending on whether most of its points were recorded while a mouse button was held down.

The result of this process is a set of 109,948 strokes from the 1,271 sessions. Each stroke is stored with its points,
its type and the session it came from, and these strokes are the units compared in the shape-matching process.

### Stroke Normalization

The users in the dataset differ in screen resolution, from 1280 × 800 to 1920 × 1080 pixels, and in logging rate:
about every 16 milliseconds for three users and about every 110 milliseconds for the rest. Raw strokes compared
directly would partly measure these hardware differences instead of the user's behavior. To compare only the shape of
each stroke, the researchers moved every stroke so that it starts at the origin, scaled it so that the diagonal of its
bounding box equals one, and redrew it as 64 points spaced evenly along its path. A stroke in which the cursor did not
actually move cannot be scaled. Such strokes were left out of the comparison but still counted toward their session's
total number of strokes.

The result is a uniform representation in which every stroke has the same number of points and the same scale, no
matter where on the screen it was drawn, how large it was, or how often its points were recorded.

### Shape Matching and Session Decision

The normalized strokes were compared using Dynamic Time Warping (DTW), which measures the distance between two
sequences while allowing one to be stretched or compressed against the other. The researchers limited this stretching
to 10 percent of the stroke length (6 of the 64 points) and compared only strokes of the same type: move with move,
drag with drag. For each stroke of a tested session, the smallest DTW distance to any stroke of the same type in a
user's library was taken. The stroke was counted as a match when its average distance per point did not exceed the
sensitivity value. A lower sensitivity is therefore stricter, because two strokes must be closer in shape before they
count as a match.

A session was accepted as belonging to the owner of the library when at least 20 percent of its strokes matched;
otherwise it was rejected. Each user's sessions were shuffled once into a fixed order. A legitimate user's library
consists of the first *k* sessions in this order, and the user is tested with their last *k* sessions, which never
appear in the library. An impostor is tested with their first *k* sessions against every legitimate user's library.
The library that accepts the most of the impostor's sessions is used, which represents the legitimate user the
impostor resembles most.

The result of this process is one decision for every tested session: accepted as the legitimate user, or rejected as
an impostor.

### Experimental Setup and Evaluation

The researchers evaluated the method on four user splits, written as impostors × legitimate users: 1 × 5, 5 × 1,
3 × 2 and 2 × 3. Every tested session counts as one decision, with the impostor as the positive class. A true positive
(TP) is an impostor session that was rejected, and a false negative (FN) is an impostor session that was accepted. A
true negative (TN) is a legitimate session that was accepted, and a false positive (FP) is a legitimate session that
was wrongly rejected. Accuracy was computed as (TP + TN) / (TP + TN + FP + FN).

Two experiments were conducted. Experiment 1 (User × User × Sensitivity) used one session per user and tested every
sensitivity from 0.01 to 1.00 in steps of 0.01. Experiment 2 (User × Sensitivity × Session) fixed the sensitivity at
Experiment 1's best value and tested libraries of 5, 10, 15 and so on up to 40 sessions per user. In both experiments,
the counts of each iteration were added to those of the iterations before it. The accuracy graphs plot these running
totals for each split: legitimate accuracy as TN / (TN + FP) and impostor accuracy as TP / (TP + FN). The best setting
was chosen from each iteration's own counts, with all splits combined. The confusion matrix of each experiment is the
running total at the last iteration, with all splits combined.

### Results of Experiment 1

Experiment 1 reached its highest accuracy at a sensitivity of 0.06. At this setting, the four splits together gave 10
true positives, 5 false positives, 1 false negative and 6 true negatives, for an accuracy of 0.727. The method rejected
10 of the 11 impostor sessions, but it also rejected 5 of the 11 legitimate sessions. Table X shows the confusion
matrix over all 100 sensitivities.

**Table X.** Confusion matrix of Experiment 1 (all sensitivities, all splits)

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Rejected (Impostor)** | TP = 68 | FP = 86 |
| **Accepted (Legitimate)** | FN = 1,032 | TN = 1,014 |

Most sessions of both classes fall in the accepted row. As the sensitivity increases, almost every stroke finds a
match, so nearly every session is accepted whether it comes from the legitimate user or from an impostor.

### Results of Experiment 2

With the sensitivity fixed at 0.06, the highest accuracy was 0.50, reached at 20 sessions per user. At this point all
220 legitimate sessions and all 220 impostor sessions were accepted. Table Y shows the confusion matrix over all eight
session counts.

**Table Y.** Confusion matrix of Experiment 2 (sensitivity 0.06, all session counts, all splits)

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Rejected (Impostor)** | TP = 0 | FP = 28 |
| **Accepted (Legitimate)** | FN = 1,980 | TN = 1,952 |

Not one impostor session was rejected at any library size. A larger library gives an impostor's strokes more chances
to find a similar shape, so once a library holds five or more sessions, every impostor session goes past the 20
percent threshold.

These initial results suggest that, at the settings tested, matching the shapes of individual strokes does not
separate one user from another. When the matched pairs were inspected, they were mostly near-straight lines, a shape
that every user produces. Other random user draws gave similar results: seed 945 gave a best sensitivity of 0.05
(accuracy 0.727) and seed 989 gave 0.01 (accuracy 0.50). Further work is needed to identify stroke features that vary
less within a user than between users.

---

# Technical Reference: From Raw Mouse Data to the Confusion Matrix

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

---

## 4.1 Data Source and Cleaning

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

## 4.2 Session Pools and User Draw

Each user $u$ has a session pool $P_u$: all of the user's remaining sessions, shuffled once with a random generator
seeded by the string `"<seed>-<user>"`. The pool order is fixed for the whole run, so a library of $k+1$ sessions always
contains the library of $k$ sessions.

A run is defined by a split $(L, I)$, a sensitivity $s$ and a session count $k$. One random draw from the seed picks
$L$ legitimate users and then $I$ impostor users from the rest, with $L + I \le 10$. Experiments 1 and 2 use four
splits, written $I \times L$: $1 \times 5$, $5 \times 1$, $3 \times 2$ and $2 \times 3$.

From the pool, three disjoint sets of sessions are taken:

| Set | Sessions | Role |
|---|---|---|
| Library $\mathcal{L}_u$ of legitimate user $u$ | first $k$ of $P_u$ | enrolled reference strokes |
| Legitimate test sessions of $u$ | last $k$ of $P_u$ | genuine attempts, never in the library |
| Impostor test sessions of impostor $v$ | first $k$ of $P_v$ | attack attempts |

Because the smallest pool has 87 sessions and the largest $k$ is 40, the first and last $k$ sessions of a legitimate
pool never overlap.

## 4.3 Stroke Segmentation

A session is cut into *strokes* (also called chunks in the code), each a short continuous pointer movement.

1. Click events (`Pressed`, `Released`) are removed from the point sequence, but each one marks a boundary: the next
   point starts a new stroke.
2. A new stroke also starts whenever the time gap between two consecutive points exceeds $\tau = 0.5$ s.
3. A stroke with fewer than 10 recorded points is discarded as jitter. (A minimum path length can also be set; it is
   0 px, i.e. off, in this experiment.)
4. Each stroke is labelled **drag** if more than half of its points have `state = Drag`, and **move** otherwise.

A stroke is kept as the array of its points $(x_i, y_i, t_i)$. The number of strokes kept in this step is the
session's stroke count $n$, which is later used as the denominator of the session ratio (Section 4.6).

## 4.4 Stroke Normalization and Resampling

Users differ in screen size (1280×800 to 1920×1080) and logging rate (about 16 ms for `user7`, `user9` and `user20`,
about 110 ms for the rest). To compare the *shape* of a stroke rather than its position, size or sampling, each stroke
is normalized as follows:

1. **Translation.** The first point is moved to the origin: $\mathbf{p}_i' = \mathbf{p}_i - \mathbf{p}_1$.
2. **Scale.** The coordinates are divided by the diagonal of the stroke's bounding box,
   $d = \sqrt{(\max x' - \min x')^2 + (\max y' - \min y')^2}$, so every stroke has a bounding-box diagonal of 1.
3. **Resampling.** The stroke is redrawn with $N = 64$ points evenly spaced along its arc length by linear
   interpolation, so every stroke has the same number of points regardless of its duration or sampling rate.

If $d = 0$ or the arc length is 0 (the pointer did not move), the stroke cannot be normalized. It is left out of the
comparison but still counts in the session's stroke count $n$, so it can never be matched.

Timing is not used after this step: the comparison is on the normalized 2-D shape only.

## 4.5 Stroke Comparison: Banded DTW and Sensitivity

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

## 4.6 Session Decision

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

## 4.7 From Sessions to Confusion Counts

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
flag is not used in the confusion matrix, which counts sessions.)

## 4.8 Experiments 1 and 2

Each *point* of an experiment is one run for every split, i.e. one $(s, k)$ setting tested on the four splits.

**Experiment 1 (User × User × Sensitivity).** The session count is fixed at $k = 1$ and the sensitivity takes every
value $s = 0.01, 0.02, \dots, 1.00$ (100 points). With $k = 1$, each point tests
$5 + 1 + 2 + 3 = 11$ legitimate sessions and $1 + 5 + 3 + 2 = 11$ impostor sessions over the four splits.

**Experiment 2 (User × Sensitivity × Session).** The sensitivity is fixed at Experiment 1's best value $s^*$ and the
session count takes $k = 5, 10, \dots, 40$ (8 points). Each point tests $11k$ legitimate and $11k$ impostor sessions.

The processing of each experiment is:

1. **Counts per point and split.** Run the procedure of Sections 4.2–4.7 and record TP, FP, FN and TN.
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

## 4.9 Worked Example: Seed 946

For seed 946 (results folder `runs/a6e6f7/`), Experiment 1 reaches its highest accuracy at $s^* = 0.06$. At that
point the four splits together give TP = 10, FP = 5, FN = 1 and TN = 6, so

$$
\text{Accuracy} = \frac{10 + 6}{10 + 6 + 5 + 1} = \frac{16}{22} = 0.727.
$$

Ten of the eleven impostor sessions are rejected, but five of the eleven legitimate sessions are rejected as well.

Experiment 1's confusion matrix (running total over all 100 sensitivities and four splits):

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Rejected** | TP = 68 | FP = 86 |
| **Accepted** | FN = 1,032 | TN = 1,014 |

Experiment 2 fixes $s = 0.06$. Its best point is $k = 20$ sessions, with TP = 0, FP = 0, FN = 220 and TN = 220
(accuracy 0.50): every session, legitimate or impostor, is accepted. Its confusion matrix over all eight session counts:

| | Actual: Impostor | Actual: Legitimate |
|---|---|---|
| **Rejected** | TP = 0 | FP = 28 |
| **Accepted** | FN = 1,980 | TN = 1,952 |

Two effects explain these numbers. In Experiment 1, the running total is dominated by the large sensitivities, at
which almost every stroke matches and almost every session passes, so most sessions of both classes fall in the
*accepted* row. In Experiment 2, a larger library offers more strokes to match against, so at $s = 0.06$ every
impostor session clears the 20% ratio once $k \ge 5$. In both experiments the accepted row grows for impostors and
legitimate users alike, which indicates that the stroke-shape match does not, at these settings, separate one user
from another.

## 4.10 Summary of Parameters

| Symbol | Setting | Value | Stage |
|---|---|---|---|
| — | `labels_file` | sessions with `is_illegal = 1` dropped | 4.1 |
| — | `seed` | 946 (also 945, 947–949, …) | 4.2 |
| $(L, I)$ | `splits` | (5, 1), (1, 5), (2, 3), (3, 2) | 4.2 |
| $\tau$ | `pause_gap_s` | 0.5 s | 4.3 |
| — | `min_points` | 10 | 4.3 |
| — | `min_length_px` | 0 (off) | 4.3 |
| $N$ | `resample_n` | 64 | 4.4 |
| $w$ | `dtw_band` | $0.1 \cdot N$ = 6 points | 4.5 |
| $s$ | `sensitivity` | 0.01–1.00 (Exp. 1); $s^*$ (Exp. 2) | 4.5 |
| $\rho$ | `match_shape_ratio` | 0.2 | 4.6 |
| $k$ | `sessions_per_user` | 1 (Exp. 1); 5–40 (Exp. 2) | 4.2, 4.8 |
