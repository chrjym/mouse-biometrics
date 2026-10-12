# Chapter 3: Methodology

> Draft, 2026-10-12. Describes what `experiment_earl/` implements as of commit `6827a6e`. Parameter values are the committed defaults in `experiment_earl/config.yaml`. Items marked **[CITATION NEEDED]** have no matching entry in `paper/references/` yet and must be filled with a verified source before submission.

## 3.1 Research Design

This study follows a quantitative, experimental design. Its question is narrow: do short mouse strokes carry enough user-specific structure to tell one person from another? Following the adviser's scope (2026-08-31), the unit of analysis is the short trajectory, not the full session. A session is cut into strokes, each stroke is described, and a user is represented by the collection of strokes recorded during enrollment. Every later decision about a session is built from decisions about its strokes.

Two experiments test the question from different angles. Experiment 1 asks whether the stroke *shapes* of one user reappear in another user's data, using elastic shape matching between libraries of normalized strokes. Experiment 2 recasts the problem as continuous authentication: each user gets a one-class model built from their own sessions only, and later sessions are scored window by window. Three models are compared under one protocol: a concave hull over stroke displacements, a One-Class Support Vector Machine (OC-SVM) over per-stroke features, and a library of stroke shapes matched with Dynamic Time Warping (DTW). A third study varies the number of enrollment sessions to see whether more enrollment data improves separation.

All settings live in a single configuration file, and every random choice is seeded. The same configuration therefore reproduces the same users, sessions and results.

## 3.2 Dataset

### 3.2.1 Source

The experiments use the Balabit Mouse Dynamics Challenge dataset **[CITATION NEEDED: Balabit Mouse Dynamics Challenge dataset]**, which records the mouse activity of 10 users (user7, user9, user12, user15, user16, user20, user21, user23, user29 and user35) working on remote desktop sessions. Each row of a session file holds a record timestamp, a client timestamp, the button, the state (`Move`, `Drag`, `Pressed` or `Released`) and the cursor position $(x, y)$ in screen pixels, with $y$ growing downward.

The dataset is split into two folders. `training_files` holds 65 sessions, five to seven per user, all produced by the folder's owner. `test_files` holds 1,611 shorter sessions that mix genuine and impostor activity. Balabit's public label file covers only 816 of them.

### 3.2.2 Session ownership

Following the adviser's instruction of 2026-10-08 to use all of the data, both folders enter the session pool. The group then decided to use the data raw: a session belongs to the user whose folder contains it, for training and test files alike, and the public label file is not used. This gives each user a pool of 114 to 253 sessions. Within a pool, training sessions come first and test sessions follow, each part shuffled with a seeded generator, so the first five sessions of any user are always genuine training sessions.

The folder-ownership rule is exact for training files and only an assumption for test files, since roughly half of the labeled test sessions are impostors. For that reason, the anomaly tests of Experiment 2 (Section 3.6) use training sessions only, where ownership is certain.

### 3.2.3 Known sources of bias

Two hardware differences between users could masquerade as behavior. Users 7, 9 and 20 log a point roughly every 16 ms, while the other seven log roughly every 110 ms. Screen resolutions also differ, from 1280×800 (user23) to 1920×1080 (users 15 and 16). Any feature that depends on point count or absolute extent partly measures the machine rather than the hand. The normalization in Section 3.4.3 and the resampling control in Section 3.6.3 address these effects.

## 3.3 Notation

A session is an ordered sequence of events $e_k = (x_k, y_k, t_k, s_k)$, where $(x_k, y_k)$ is the cursor position in pixels, $t_k$ the client timestamp in seconds and $s_k$ the state. A stroke (chunk) is a contiguous subsequence $C = (\mathbf{p}_1, \dots, \mathbf{p}_m)$ with $\mathbf{p}_i = (x_i, y_i)$ and times $t_1 \le \dots \le t_m$. For a user $u$, $\mathcal{E}_u$ denotes the enrollment sessions and $\mathcal{L}_u$ the strokes extracted from them. Table 3.1 lists the parameters used throughout.

**Table 3.1.** Parameters and their default values.

| Symbol | Config key | Default | Meaning |
|---|---|---|---|
| $g$ | `pause_gap_s` | 0.5 s | Pause that ends a stroke |
| $m_{\min}$ | `min_points` | 10 | Minimum points per stroke |
| $n$ | `resample_n` | 64 | Points per resampled stroke |
| $\beta$ | `dtw_band` | 0.1 | DTW band width as a share of $n$ |
| $\tau$ | `dtw_tolerance` | 0.02 | Mean DTW cost per point for a match |
| $\rho_s$ | `match_shape_ratio` | 0.3 | Share of matching strokes for a session match |
| $\rho_u$ | `match_session_ratio` | 0.5 | Share of matching sessions for a user match |
| $k$ | `anomaly_enroll_sessions` | 4 | Enrollment sessions per user (Experiment 2) |
| $W$ | `anomaly_window` | 30 | Strokes per sliding window |
| $\theta$ | `anomaly_outside_share` | 0.2 | Outside share that flags a window |
| $\alpha$ | `concave_ratio` | 0.1 | Concave hull tightness |
| $\nu$ | `ocsvm_nu` | 0.05 | OC-SVM outlier fraction |
| $N_L$, $N_I$ | `n_legitimate`, `n_impostor` | 3, 2 | Legitimate and impostor users (one fixed draw) |
| $T$ | `n_trials` | 20 | Random draws per sweep cell (Section 3.5.3 only) |

## 3.4 Preprocessing and Stroke Extraction

### 3.4.1 Cleaning

Each session is loaded in four steps. Rows with missing time or position are dropped. Scroll events are removed because they carry no cursor path. Rows with $x = 65535$ or $y = 65535$ are removed as well; these are logging glitches, and left in place they create jumps of about 60,000 pixels. Finally, rows are ordered by client timestamp with a *stable* sort. Balabit timestamps tie often, and an unstable sort would reorder tied rows and corrupt the path. Times are shifted so that each session starts at $t = 0$.

### 3.4.2 Segmentation

A session is split into strokes at two kinds of boundaries. A new stroke starts whenever the gap between consecutive events exceeds $g$:

$$t_{k} - t_{k-1} > g, \qquad g = 0.5\ \text{s}.$$

Every click (`Pressed` or `Released` event) also starts a new stroke, and click rows themselves are not part of any path. Strokes with fewer than $m_{\min} = 10$ points are discarded as jitter. A stroke is labeled a *drag* when more than half of its points have state `Drag`, and a *move* otherwise. The two kinds are kept apart in all shape comparisons.

Pause-based segmentation answers the adviser's open question about what a "short signal" is in an operational way: a stroke is one continuous burst of movement between pauses or clicks.

### 3.4.3 Shape normalization

Shape matching needs strokes that are comparable regardless of where on the screen they occurred, how long they were, or how fast the logger sampled them. Each stroke is translated, scaled and resampled:

1. **Translation.** $\mathbf{q}_i = \mathbf{p}_i - \mathbf{p}_1$, so every stroke starts at the origin.
2. **Scaling.** With $d = \sqrt{(\max_i q_{i,x} - \min_i q_{i,x})^2 + (\max_i q_{i,y} - \min_i q_{i,y})^2}$ the diagonal of the bounding box, the stroke is divided by $d$, so its bounding-box diagonal becomes 1.
3. **Arc-length resampling.** With cumulative arc length $\ell_i = \sum_{j=2}^{i} \lVert \mathbf{q}_j - \mathbf{q}_{j-1} \rVert$, the stroke is linearly interpolated at $n = 64$ points evenly spaced on $[0, \ell_m]$.

Resampling by arc length removes both the speed of the movement and the logging rate from the shape. Scaling removes the absolute size, which also removes most of the screen-resolution effect. A stroke with $d = 0$ or $\ell_m = 0$ (no movement) cannot be normalized. Such strokes are excluded from shape comparison but still counted in the denominators of Section 3.5.2, so that every recorded stroke counts.

## 3.5 Experiment 1: Cross-User Shape Matching

### 3.5.1 Elastic distance between strokes

Two normalized strokes $\mathbf{a} = (\mathbf{a}_1, \dots, \mathbf{a}_n)$ and $\mathbf{b} = (\mathbf{b}_1, \dots, \mathbf{b}_n)$ are compared with banded DTW, an elastic alignment previously used to compare repeated mouse trajectories [2]. The cumulative cost is

$$D(i, j) = \lVert \mathbf{a}_i - \mathbf{b}_j \rVert_2 + \min\{D(i-1, j-1),\ D(i-1, j),\ D(i, j-1)\},$$

with $D(0, 0) = 0$, all other boundary cells infinite, and cells outside the band $|i - j| \le w$ left infinite, where $w = \operatorname{round}(\beta n) = 6$ **[CITATION NEEDED: DTW with a Sakoe–Chiba band]**. The band stops the alignment from pairing the start of one stroke with the end of the other.

Two strokes *match* when the mean cost per point does not exceed the tolerance:

$$\text{match}(\mathbf{a}, \mathbf{b}) \iff D(n, n) \le \tau n, \qquad \tau = 0.02.$$

Because a match decision needs only a yes or no, the computation stops early once every cell of a row exceeds $\tau n$. A query stroke matches a library when at least one library stroke of the same kind (move or drag) matches it.

### 3.5.2 From strokes to users

For a session $S$ with $|S|$ recorded strokes and a legitimate user's library $\mathcal{L}_u$, the session match ratio is

$$r(S, u) = \frac{\left|\{C \in S : C \text{ matches } \mathcal{L}_u\}\right|}{|S|}.$$

Session $S$ matches profile $u$ when $r(S, u) \ge \rho_s = 0.3$. An impostor user $v$ is *matched* when at least $\rho_u = 0.5$ of their sessions match a single legitimate profile. Each profile is tested separately; the impostor is assigned to the profile with the highest share of matching sessions.

For one draw with legitimate users $L$ and impostor users $I$, the outcome is the overlap threshold

$$\Theta = \frac{\left|\{v \in I : v \text{ is matched}\}\right|}{|I|} \in [0, 1].$$

A value of 0 means no impostor resembles any legitimate user, which is the desired outcome. As a sanity check, each legitimate user's held-out sessions are scored against their own library; if shapes are user-specific, these ratios should exceed those of impostors.

### 3.5.3 Sampling and sweep

In each draw, the 10 users are shuffled once with a seeded generator. Legitimate users are taken from the front of the list and impostors from the back, and each user contributes the first $s$ sessions of their shuffled pool. This nesting means that a cell with $s + 1$ sessions or one more user contains every session of the smaller cell, so neighboring cells differ only by the added data.

The sweep covers every combination of $s \in \{1, \dots, 5\}$ sessions per user, $|L| \in \{1, \dots, 9\}$ legitimate users and $|I| \in \{1, \dots, 10 - |L|\}$ impostors, over $T = 20$ draws. Since Balabit has only 10 users, $|L| + |I| \le 10$. Each (impostor, legitimate) pair is scored once per draw and all cells are assembled from those pair results. For every curve, the analysis records the step after which $\Theta$ changes by less than $\delta = 0.05$ (saturation) and the largest single jump.

### 3.5.4 Choice of tolerance

The tolerance $\tau$ was tuned empirically. At $\tau = 0.15$, about 99% of all strokes found a match, so the measure carried no information. At $\tau = 0.02$ results are neither all 0 nor all 1. This value is a working baseline chosen to keep the measure informative; it was not selected for separating users.

## 3.6 Experiment 2: One-Class Anomaly Detection

Experiment 2 reframes the question as continuous authentication. Each user is enrolled from their own data only, without impostor examples, and later sessions are scored stroke by stroke. Three one-class models share one protocol, which makes their error rates directly comparable.

### 3.6.1 Common protocol

Only training sessions are used (Section 3.2.2). Per user, every training session is scored in two roles:

- **Genuine (leave-one-out).** Each of the user's training sessions is held out in turn. The model is built from $k = 4$ sessions drawn at random from the remaining ones and then scores the held-out session. These scores give the false rejection rate.
- **Impostor.** One model is built from $k$ of the user's training sessions and scores every training session of the other nine users. These scores give the false acceptance rate.

The enrollment draws are seeded per user and per held-out session, and all three models use exactly the same draws.

**Windowing.** Each stroke $C_j$ of a scored session receives an anomaly indicator or score from the model (Sections 3.6.2–3.6.4). The session is then read through a sliding window of $W = 30$ consecutive strokes, moving one stroke at a time. A session shorter than $W$ strokes forms a single window. For the hull and DTW models, with $o_j \in \{0, 1\}$ marking an anomalous stroke, window $w$ has outside share

$$\bar{o}_w = \frac{1}{W} \sum_{j=w}^{w+W-1} o_j,$$

and is flagged when $\bar{o}_w > \theta = 0.2$. A session is flagged when any of its windows is flagged, and its session score is the worst window, $\max_w \bar{o}_w$.

### 3.6.2 Model A: Concave hull of stroke displacements

Each stroke is reduced to a single point, its net displacement $\mathbf{d}_j = \mathbf{p}_m - \mathbf{p}_1 = (\Delta x, \Delta y)$. In other words, every stroke is moved to start at the origin and only its end point is kept. The user's profile is the concave hull of all distinct displacement points from the enrollment sessions, computed with tightness $\alpha = 0.1$, where 0 gives the tightest outline and 1 the convex hull **[CITATION NEEDED: concave hull algorithm]**. A stroke is anomalous ($o_j = 1$) when its displacement lies outside the hull.

The hull captures *where* a user tends to move (direction and reach) and ignores the path in between. Because displacements are measured in pixels, the hull also inherits screen size, which is a known limitation of this model.

### 3.6.3 Model B: One-Class SVM on stroke features

Each stroke is described by six features (Table 3.2), chosen to cover direction, extent, shape and timing.

**Table 3.2.** Per-stroke features for the OC-SVM.

| Feature | Definition |
|---|---|
| $\Delta x$, $\Delta y$ | Net displacement in pixels (the hull's point) |
| Path length | $\log(1 + \ell)$, with $\ell$ the summed segment length in pixels |
| Straightness | $\lVert \mathbf{d} \rVert / \ell$ (1 for a straight line; 0 when $\ell = 0$) |
| Mean speed | $\log(1 + \ell / \Delta t)$, in pixels per second |
| Duration | $\Delta t = t_m - t_1$ in seconds, floored at 1 ms to avoid division by zero |

Similar compact sets of geometric and kinematic features have been scored with one-class models in prior work on Balabit [3], and OC-SVMs are a common one-class profile for mouse data [1]. Features are scaled with a robust scaler (median and interquartile range), and an OC-SVM with a radial basis function kernel and $\nu = 0.05$ is fitted to the enrollment strokes **[CITATION NEEDED: One-Class SVM]**. The parameter $\nu$ bounds the share of the user's own training strokes allowed outside the learned region. To keep training time bounded, at most 4,000 enrollment strokes are sampled at random per model.

For each stroke the model returns a signed decision value $f(\mathbf{x}_j)$, positive inside the user's region and negative outside. Window scores are means of $f$ over $W$ strokes, a window is flagged when its mean falls below 0, and the session score is the lowest window mean.

Path length, straightness and speed depend on how often points are logged. As a control, the features can be computed on a path resampled to a fixed 125 ms grid (holding the last logged position), which puts the 16 ms and 110 ms loggers on equal footing. Net displacement and duration are unaffected by this resampling.

### 3.6.4 Model C: DTW shape library

The third model reuses the shape matching of Experiment 1 inside the anomaly protocol. The user's library contains the normalized strokes (Section 3.4.3) of the enrollment sessions, capped at 4,000 shapes chosen at random (the same cap as the OC-SVM) and split by kind. A stroke is anomalous when no library shape of its kind lies within tolerance $\tau$ (Section 3.5.1). Strokes that cannot be normalized are left out. Windowing and flagging follow Section 3.6.1 exactly as for the hull.

### 3.6.5 Fixed legitimate and impostor users

Every profile is scored once against every other user's sessions. A single seeded draw then fixes $N_L = 3$ users as legitimate profiles and $N_I = 2$ of the remaining users as impostors. Once drawn, these roles never change: every model, enrollment size and figure in a run uses the same users and sessions. The false rejection rate comes from the legitimate users' own held-out sessions. The false acceptance rate comes only from the impostors' sessions scored against those profiles. Both are pooled over the legitimate users. Per-user rates, in which each profile faces all nine other users, are reported alongside.

### 3.6.6 Enrollment-size study

To test whether more enrollment data sharpens the profiles, all three models are rerun with $k = 1, 2, 3, 4$ enrollment sessions. Since the seeded random sample of $k$ sessions is a prefix of the same draw for every $k$, each step adds sessions to the previous one instead of drawing new ones, and the $k = 4$ step reproduces the main results. The study reports FRR, FAR and EER per method and $k$.

## 3.7 Evaluation Metrics

For a set of genuine session scores $G$ and impostor session scores $M$, and a cut $c$ on the session score, the false rejection and false acceptance rates are

$$\text{FRR}(c) = \frac{|\{g \in G : g \text{ rejected at } c\}|}{|G|}, \qquad \text{FAR}(c) = \frac{|\{h \in M : h \text{ accepted at } c\}|}{|M|}.$$

For the hull and DTW models a session is rejected when its worst-window outside share reaches $c$; for the OC-SVM, when its lowest window mean falls below $c$. The equal error rate (EER) is found by scanning every observed score as a cut, picking the cut $c^*$ that minimizes $|\text{FRR}(c) - \text{FAR}(c)|$, and reporting $\text{EER} = \tfrac{1}{2}\left(\text{FRR}(c^*) + \text{FAR}(c^*)\right)$.

FRR and FAR are also reported at the fixed operating rules ($\theta = 0.2$ for hull and DTW, score 0 for the OC-SVM). These fixed rules can sit far from the equal-error point; for that reason, methods are compared by EER, which does not depend on the operating rule. Experiment 1 reports the overlap threshold $\Theta$ of Section 3.5.2 and, for the held-out sanity check, the separation between own-session and impostor-session match ratios.

## 3.8 Implementation

The pipeline is written in Python 3 with NumPy and pandas for data handling, Numba for the parallel banded DTW, Shapely for the convex and concave hulls, scikit-learn for the robust scaler and OC-SVM, and Matplotlib for figures. It is organized as numbered scripts, one per stage (Table 3.3).

**Table 3.3.** Pipeline stages.

| Script | Stage |
|---|---|
| `01_sample_users`, `02_sample_sessions` | Seeded draw of legitimate and impostor users and their sessions |
| `03_chunk_shapes` | Cleaning, segmentation, normalization (Section 3.4) |
| `04_match_shapes`, `05_threshold` | DTW matching and overlap threshold for one draw (Section 3.5) |
| `06_sweep` | Full sessions × legitimate × impostor sweep |
| `09_build_hulls` | Per-user displacement hulls |
| `10_hull_anomaly`, `11_ocsvm_anomaly`, `12_dtw_anomaly` | Models A, B and C (Section 3.6) |
| `13_enroll_sweep` | Enrollment-size study (Section 3.6.6) |

Every script reads the same configuration file. Each distinct configuration is hashed and its outputs are written to a separate run folder together with a snapshot of the configuration and the code version, so a change of settings never overwrites earlier results. DTW pair results are cached across runs under keys that include the segmentation, band and tolerance settings. **[TO FILL: hardware used for the reported runs.]**

## 3.9 Threats to Validity

- **Small population.** Balabit has 10 users, so at most 10 legitimate and impostor users can appear in one draw, and per-user results rest on five to seven training sessions. The headline results come from one fixed draw of users and sessions, so they describe those users; the sweep's 20 draws (Section 3.5.3) show how results change across user combinations, but neither can replace a larger cohort.
- **Hardware confounds.** Logging rate and screen size differ by user (Section 3.2.3). Shape normalization removes both from Model C and Experiment 1, and the 125 ms resampling control tests their effect on Model B. Model A works in raw pixels and remains exposed to screen size.
- **Test-file ownership.** Assigning test sessions to their folder's owner is unverified for about half of the labeled ones. Experiment 2 avoids the issue by using training files only, while Experiment 1 uses test files only when more than five sessions per user are requested.
- **Parameter selection.** $\tau$, $\theta$, $W$ and $\nu$ were set on the same data that is evaluated, without a separate tuning split. EER limits the effect of the operating rule but not of the other parameters.
- **Divergence from the proposed method.** The original proposal named discrete Fréchet distance, closed-form curvature descriptors and a dynamic trust threshold. The implemented pipeline uses DTW for shape comparison and fixed window rules for decisions. The closed-form descriptors and Fréchet comparison remain future work.

## References

[1] M. Antal, N. Fejér, and K. Búza, "SapiMouse: Mouse dynamics-based user authentication using deep feature learning," in *Proc. IEEE 15th Int. Symp. Applied Computational Intelligence and Informatics (SACI)*, 2021, pp. 273–278, doi: 10.1109/SACI51354.2021.9465583.

[2] S. Sadeghpour and N. Vlajic, "ReMouse dataset: Measuring the similarity of human-generated trajectories for session-replay bot detection," *J. Cybersecurity and Privacy*, vol. 3, no. 1, pp. 95–117, 2023, doi: 10.3390/jcp3010007.

[3] A. Awad, H. Abouelseoud, and M. W. Fakhr, "One-class Mahalanobis profiles for compact mouse dynamics authentication," *IEEE Access*, vol. 8, pp. 159689–159704, 2020, doi: 10.1109/ACCESS.2020.3020087.
