# `08_plot_matches.py`: draw the impostor strokes that matched a user

[← index](README.md) · next: [09](09_genuine_check.md)

## What it does

The notebook ([07](07_run_notebook.md)) only *counts* impostors that match each legitimate user. This script
shows **which strokes** matched, by drawing each matched impostor stroke on top of the user's stroke it matched.
It answers the question "what shapes make two different people look the same?"

Output: `runs/<run>/results/matches.csv` (every matched pair). No figures are drawn (removed 2026-10-26); the console
prints each impostor's verdict.

## Algorithm

### 1. Reproduce the notebook's draw (`draw_users`)

```
rng        ← Random(seed)
legitimate ← rng.sample(users, n_legitimate)               # kept in draw order (heatmap columns)
impostor   ← sorted(rng.sample(the others, n_impostor))
order[u]   ← session_pool(u, seed) for every chosen user
```

These are the same calls as script 01, so the users are the same (only the order of the legitimate users
differs). Script 09 reuses this function.

### 2. For each legitimate user and session step k (`step_matches`)

```
library ← the user's first k sessions (normalized shapes, from 04.dataset_session)
for each impostor, each of their first k sessions, each kind (move/drag):
    for each library session j (in order):
        idx ← first_match(impostor shapes, library_j shapes, band, cap)     # cached per pair
        strokes not yet matched that match here ← (library session j, index idx)
    for every matched stroke: record the pair and its DTW cost per point
```

### `first_match`: the same search as `has_match`, but returning *which* stroke

`has_match` (04) returns only true/false. Both use banded DTW [[1]](#ref-1), [[2]](#ref-2). `first_match` runs the same loop (same `_dtw_within`, same band, same
cap, same order) and returns the **index** of the first library stroke within the cap, or −1. Because the search
and its order are identical, a stroke counts as matched here exactly when it counts as matched in the notebook.

### `dtw_cost`: the full DTW value of a matched pair

`_dtw_within` stops early and only answers yes/no. To print the actual cost in each panel (compiled with numba [[3]](#ref-3)), `dtw_cost` fills the
whole banded DTW table (the recurrence in [04](04_match_shapes.md#the-dtw-recurrence)) and returns $D(n,n)$. The
matches.csv column shows

$$\text{cost per point} = D(n, n) / n \;\le\; \texttt{dtw\_tolerance}$$

### 3. Verdicts (`session_verdicts`)

The console line repeats the bar graph's decision for each impostor, with the rules of 04:

$$r_s = \frac{\text{matched strokes of } s}{\text{strokes of } s}, \qquad
\text{MATCHED} \iff \frac{|\{s : r_s \ge \sigma\}|}{k} \ge \rho$$

On runs `oct12_test2_d4015c` and `oct12_test2_e36855`, all 30 verdicts agree with
`session_progression_users.csv`, which confirms that the script and the notebook compute the same thing.

## Why

Counts alone cannot explain **why** impostors pass. The matched pairs in `matches.csv` can, when drawn with another
tool. They also check the matcher: if the matched strokes did not look alike, the tolerance or the normalization
would be wrong.

## What we learned

Matched pairs are mostly **near-straight lines**. After normalization, a straight move from A to B looks the same
for everyone, which is why shapes match across users and why shape matching alone cannot tell users apart.
About 2 minutes for 6 users × 5 steps.

## References

<a id="ref-1"></a>[1] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).

<a id="ref-2"></a>[2] E. Keogh and C. A. Ratanamahatana, "Exact indexing of dynamic time warping," *Knowl. Inf. Syst.*, vol. 7, no. 3, pp. 358–386, Mar. 2005, doi: [10.1007/s10115-004-0154-9](https://doi.org/10.1007/s10115-004-0154-9).

<a id="ref-3"></a>[3] S. K. Lam, A. Pitrou, and S. Seibert, "Numba: A LLVM-based Python JIT compiler," in *Proc. 2nd Workshop LLVM Compiler Infrastructure HPC*, 2015, pp. 1–6, doi: [10.1145/2833157.2833162](https://doi.org/10.1145/2833157.2833162).
