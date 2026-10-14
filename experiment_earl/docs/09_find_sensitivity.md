# `09_find_sensitivity.py`: find the sensitivity (User × User × Sensitivity)

[← index](README.md) · next: [10](10_find_session.md)

## What it does

First step of the adviser's pipeline (2026-10-14):

```
raw → RNG (legitimate users, impostor users, sessions) → strokes (chunk shapes)
    → user × user × sensitivity (09) → user × session × sensitivity (10) → sensitivity → heatmap (10)
```

It uses only the main configuration (user decision 2026-10-14): the notebook's draw from `seed`
(`n_legitimate` legitimate users in draw order, `n_impostor` impostors, each user's session order), the
configured **sensitivity** (the DTW tolerance of script 04, config key `sensitivity`, formerly `dtw_tolerance`)
and `sessions_per_user`. To compare sensitivities, change `sensitivity` and rerun; each value gets its own run
folder. Matching uses DTW only.

Outputs: `runs/<run>/results/sensitivity/users.csv`, `results/sensitivity/summary.csv`,
`figures/find_sensitivity.png`.

## Algorithm

```
L, I, order ← 14.draw_users(config, seed)                       # the notebook's draw
T[u] ← order[u][sessions_per_user : sessions_per_user + 2]      # tested sessions, never in a profile
for each legitimate profile p, each user u in L ∪ I:
    library ← p's first sessions_per_user sessions
    hit[p, u][s] ← r(s, library) ≥ match_shape_ratio  for s in T[u]     # r: 04's session match ratio at τ
legitimate u: accuracy = mean(hit[u, u]);  accepted  = accuracy ≥ match_session_ratio
impostor v:   accuracy = share of s in T[v] with no p in L having hit[p, v][s]
              through  = some p in L has mean(hit[p, v]) ≥ match_session_ratio
```

## Formulas

Per user, with $T_u$ the tested sessions and $\tau$ the sensitivity:

$$\text{Acc}(u) = \frac{|\{s \in T_u : s \text{ matches } u\text{'s profile}\}|}{|T_u|} \ (u \in L),\qquad
\text{Acc}(v) = \frac{|\{s \in T_v : \text{no } p \in L \text{ matches } s\}|}{|T_v|} \ (v \in I)$$

Overall (`summary.csv`):

$$\text{Acc}_L = \frac{|\{u \in L : u \text{ accepted}\}|}{|L|},\qquad
\text{Acc}_I = 1 - \frac{|\{v \in I : v \text{ through}\}|}{|I|},\qquad
\text{Acc} = \tfrac12(\text{Acc}_L + \text{Acc}_I)$$

$1 - \text{Acc}_L$ is a user-level false rejection rate and $1 - \text{Acc}_I$ a user-level false acceptance
rate [[1]](#ref-1); their mean is balanced accuracy, so 1 legitimate user and 4 impostors weigh both sides
equally. `impostor_sensitivity` $= 1 - \text{Acc}_I$ is the old *threshold* (impostors through / impostors).

## Why these choices

- **One configuration for every script:** 09 and 10 see the same users, sessions and tolerance as the notebook
  and scripts 01–05, 14 and 15, so their numbers can be compared directly.
- **x = each user** (whiteboard axis "1, 2, …, I, …, n"): with one draw there is one legitimate set and one
  impostor set, so the graphs show every user separately instead of a count.
- **Tested sessions after the profile:** a legitimate user's tested sessions are never part of their own
  profile, at any session step of script 10.

## What we learned

- With the adviser's tolerances 0.2–1.0 (earlier version, `oct14_exp1_23ed6f`), every legitimate user was
  accepted and every impostor went through. Banded DTW [[2]](#ref-2) on normalized strokes is already
  permissive at 0.15 (about 99% of strokes match).
- At 0.02 (`oct14_exp1_c8f010`, user20 vs user21, user23, user29, user35): no impostor session matches, but
  neither do user20's own (accuracy 0.50).

## Settings used

`seed`, `n_legitimate`, `n_impostor`, `sessions_per_user`, `sensitivity`, the chunking settings, `dtw_band`,
`match_shape_ratio`, `match_session_ratio`.

## References

<a id="ref-1"></a>[1] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).

<a id="ref-2"></a>[2] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).
