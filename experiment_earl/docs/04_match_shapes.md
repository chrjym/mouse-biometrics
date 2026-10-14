# `04_match_shapes.py`: banded DTW shape matching

[← index](README.md) · previous: [03](03_chunk_shapes.md) · next: [05](05_threshold.md)

## What it does

Step 4 of the single trial, and the matching engine used by scripts 06, 12, 14 and 15. For every impostor
session it asks: **how many of its strokes have a near-identical stroke in a legitimate user's library?** Then it
decides, in three levels (stroke → session → user), whether the impostor "matched" that user.

Output: `runs/<run>/results/trial_<k>.json` (one record per impostor, plus a sanity check on the legitimate
users' held-out sessions).

## Level 1: are two strokes the same shape? Dynamic Time Warping (DTW)

Two normalized strokes $a$ and $b$, each $n = 64$ points, are compared with **Dynamic Time Warping** [[1]](#ref-1).

### The DTW recurrence

DTW finds the cheapest way to line up the points of $a$ with the points of $b$, where one point may be paired
with several points of the other stroke (the alignment may "stretch" or "compress" parts of a stroke). The
cost of the best alignment is computed with dynamic programming:

$$D(0, 0) = 0, \qquad D(i, 0) = D(0, j) = \infty$$

$$D(i, j) = d(a_i, b_j) + \min\big\{\, D(i-1, j-1),\; D(i-1, j),\; D(i, j-1) \,\big\}$$

where $d(a_i, b_j)$ is the Euclidean distance between the two points. $D(n, n)$ is the total DTW cost.

- $D(i-1, j-1)$: both strokes advance one point (normal step).
- $D(i-1, j)$: $a$ advances while $b$ stays (part of $b$ is stretched).
- $D(i, j-1)$: $b$ advances while $a$ stays.

### The band (Sakoe–Chiba constraint)

Only cells near the diagonal are allowed (the Sakoe–Chiba band [[1]](#ref-1), [[2]](#ref-2)):

$$|i - j| \le w, \qquad w = \operatorname{round}(\texttt{dtw\_band} \times n) = \operatorname{round}(0.1 \times 64) = 6$$

### The match rule

$$a \text{ matches } b \iff \frac{D(n, n)}{n} \le \texttt{dtw\_tolerance}$$

The code compares $D(n,n)$ with the cap $C = \texttt{dtw\_tolerance} \times n = 0.02 \times 64 = 1.28$. Because
strokes are scaled to a bounding-box diagonal of 1 (script 03), a tolerance of 0.02 means "on average each point
is within about **2% of the stroke's size** of the other stroke".

### Early abandoning (`_dtw_within`)

The code fills the DTW table row by row and keeps only two rows in memory (`prev`, `cur`). After each row it
checks the smallest value in that row:

$$\min_j D(i, j) > C \;\Rightarrow\; \text{no match, stop now}$$

This is safe because distances are never negative: every later cell is a row-$i$ value plus more non-negative
costs, so $D(n,n)$ can only be larger. Most stroke pairs are clearly different, so most comparisons stop after a
few rows. Early abandoning is a standard way to speed up DTW search [[3]](#ref-3).

### Library search (`has_match`)

For each query stroke, the library strokes are tried one by one, stopping at the **first** one within the cap.
We only need to know *whether* a match exists, not which match is best. Query strokes are processed in parallel
with numba (`prange`), and the code is compiled to machine code (`@njit`) [[4]](#ref-4), [[5]](#ref-5).

### Why DTW

- Two people tracing the "same" curve rarely do it in lock-step. One bends a little earlier, another overshoots
  and corrects. Arc-length resampling (03) removes global speed differences, but not these local timing
  shifts. DTW absorbs them by letting the alignment bend, so similar shapes get a low cost even if they are not
  aligned point by point.
- A plain point-by-point (Euclidean) distance would punish a small shift along the path as heavily as a
  completely different shape.
- DTW was the method in Earl's idea list and the execution plan, and it is the standard tool for comparing
  trajectories and time series [[2]](#ref-2), [[3]](#ref-3).

### Why a band

- **Realism:** without a band, DTW can pair one point with half of the other stroke and make very different
  shapes look alike ("pathological warping") [[1]](#ref-1), [[2]](#ref-2). A 10% band allows small local shifts only.
- **Speed:** the work per pair drops from $n^2 = 4096$ cells to about $n(2w+1) \approx 830$ cells, five times
  fewer, before early abandoning saves even more.

### Caching

A comparison depends only on (query session, library session, segmentation settings, band, tolerance). That
tuple is the key of `_PAIRS`, saved to `experiment_earl/cache/pairs.pkl` and shared by all runs, so a pair is
never computed twice. `_SESSIONS` likewise keeps each segmented file in memory.

## Level 2: does a session match a profile?

`matched_chunks` counts query strokes that match a stroke **of the same kind** in **any** session of the profile
(logical OR across library sessions). The **session match ratio** is

$$r = \frac{\#\text{matched strokes}}{\#\text{all strokes of the session}}$$

$$\text{session matches profile} \iff r \ge \sigma, \qquad \sigma = \texttt{match\_shape\_ratio}$$

The denominator counts every stroke, including ones too flat to normalize, so they count as unmatched.

## Level 3: does an impostor user match a profile? (`match_trial`)

For impostor $v$ and profile $u$, with $S_v$ the impostor's sessions:

$$\text{share}(v, u) = \frac{|\{ s \in S_v : r_{s,u} \ge \sigma \}|}{|S_v|}$$

$$v \text{ is matched} \iff \max_{u \in L}\ \text{share}(v, u) \ge \rho, \qquad \rho = \texttt{match\_session\_ratio}$$

Each legitimate profile is scored **separately**, and the impostor counts as matched if **any single** profile
accepts them. The record names the profile with the highest share (ties broken by mean ratio).

**Why per profile and not one merged library?** In continuous authentication, the system protects one account
at a time: an impostor sits at *user u's* computer. Merging all legitimate users into one library would answer a
different question ("does this look like *anyone* we know?").

**Why ratios and not a single stroke?** One stroke is very short and noisy, and some strokes (straight lines)
match everyone. Requiring a share of strokes, and then a share of sessions, makes the decision depend on many
strokes.

## Sanity check (`sanity_check`)

Each legitimate user's **held-out** sessions (never in their library) are scored against their own library.
If shape matching captured identity, these ratios should be higher than the impostors' ratios.

## Settings used

`resample_n`, `dtw_band` (0.1), `dtw_tolerance` (0.02), `match_shape_ratio`, `match_session_ratio` (0.5),
plus the segmentation settings in the cache key.

## What we learned

Chunk matching does **not** discriminate between users:

- at tolerance 0.15, about 99% of all strokes match;
- at 0.01–0.06, and with longer strokes (gap 1–3 s, minimum length 100–300 px), a user's own held-out sessions
  never match better than impostors (AUC 0.27–0.50).

The value 0.02 is kept only because it gives a non-trivial heatmap. Treat the numbers as a baseline, not as
evidence of unique shapes.

## References

<a id="ref-1"></a>[1] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).

<a id="ref-2"></a>[2] E. Keogh and C. A. Ratanamahatana, "Exact indexing of dynamic time warping," *Knowl. Inf. Syst.*, vol. 7, no. 3, pp. 358–386, Mar. 2005, doi: [10.1007/s10115-004-0154-9](https://doi.org/10.1007/s10115-004-0154-9).

<a id="ref-3"></a>[3] T. Rakthanmanon, B. Campana, A. Mueen, G. Batista, B. Westover, Q. Zhu, J. Zakaria, and E. Keogh, "Searching and mining trillions of time series subsequences under dynamic time warping," in *Proc. 18th ACM SIGKDD Int. Conf. Knowl. Discov. Data Min. (KDD)*, 2012, pp. 262–270, doi: [10.1145/2339530.2339576](https://doi.org/10.1145/2339530.2339576).

<a id="ref-4"></a>[4] S. K. Lam, A. Pitrou, and S. Seibert, "Numba: A LLVM-based Python JIT compiler," in *Proc. 2nd Workshop LLVM Compiler Infrastructure HPC*, 2015, pp. 1–6, doi: [10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162).

<a id="ref-5"></a>[5] Numba developers, "Automatic parallelization with @jit (prange)," Numba documentation. [Online]. Available: https://numba.readthedocs.io/en/stable/user/parallel.html
