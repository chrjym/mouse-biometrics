# `14_plot_matches.py`: draw the impostor strokes that matched a user

[← index](README.md) · next: [15](15_genuine_check.md)

## What it does

The notebook ([08](08_run_notebook.md)) only *counts* impostors that match each legitimate user. This script
shows **which strokes** matched, by drawing each matched impostor stroke on top of the user's stroke it matched.
It answers the question "what shapes make two different people look the same?"

Outputs: `runs/<run>/figures/matches/<user>_sessions<k>.png`, `results/matches.csv` (every matched pair).

## Algorithm

### 1. Reproduce the notebook's draw (`draw_users`)

```
rng        ← Random(seed)
legitimate ← rng.sample(users, n_legitimate)               # kept in draw order (heatmap columns)
impostor   ← sorted(rng.sample(the others, n_impostor))
order[u]   ← session_pool(u, seed) for every chosen user
```

These are the same calls as script 01, so the users are the same (only the order of the legitimate users
differs). Script 15 reuses this function.

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

`has_match` (04) returns only true/false. `first_match` runs the same loop (same `_dtw_within`, same band, same
cap, same order) and returns the **index** of the first library stroke within the cap, or −1. Because the search
and its order are identical, a stroke counts as matched here exactly when it counts as matched in the notebook.

### `dtw_cost`: the full DTW value of a matched pair

`_dtw_within` stops early and only answers yes/no. To print the actual cost in each panel, `dtw_cost` fills the
whole banded DTW table (the recurrence in [04](04_match_shapes.md#the-dtw-recurrence)) and returns $D(n,n)$. The
plot shows

$$\text{cost per point} = D(n, n) / n \;\le\; \texttt{dtw\_tolerance}$$

### 3. Verdicts (`session_verdicts`)

The figure title repeats the bar graph's decision for each impostor, with the rules of 04:

$$r_s = \frac{\text{matched strokes of } s}{\text{strokes of } s}, \qquad
\text{MATCHED} \iff \frac{|\{s : r_s \ge \sigma\}|}{k} \ge \rho$$

On runs `oct12_test2_d4015c` and `oct12_test2_e36855`, all 30 verdicts agree with
`session_progression_users.csv`, which confirms that the script and the notebook compute the same thing.

### 4. Plot (`plot_step`)

At most `--max` (36) pairs, a seeded random sample, are drawn per figure. Each panel shows the user's stroke in
blue, the impostor's stroke as a red dashed line, and the start in green, with the y axis inverted like the screen.

## Why

Counts alone cannot explain **why** impostors pass. Seeing the strokes can. It also checks the matcher: if the
overlaid strokes did not look alike, the tolerance or the normalization would be wrong.

## What we learned

Matched pairs are mostly **near-straight lines**. After normalization, a straight move from A to B looks the same
for everyone, which is why shapes match across users and why shape matching alone cannot tell users apart.
About 2 minutes for 6 users × 5 steps.
