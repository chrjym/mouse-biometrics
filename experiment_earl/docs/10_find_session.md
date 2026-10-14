# `10_find_session.py`: find the sessions (User × Session × Sensitivity) and the heatmap

[← index](README.md) · previous: [09](09_find_sensitivity.md)

## What it does

Second and last step of the adviser's pipeline (2026-10-14). Same users and tested sessions as script 09, at
the sensitivity 09 used (read from `results/sensitivity/summary.csv`, so run 09 first), with 1, 2, …
`sessions_per_user` profile sessions per legitimate user.

Outputs: `runs/<run>/results/session/{users,summary,heatmap}.csv`, `figures/find_session.png`,
`figures/sensitivity_heatmap.png`.

## Algorithm

```
L, I, order, T ← 09.draw(config)
τ ← results/sensitivity/summary.csv
for k in 1 … sessions_per_user:
    hit ← 09.session_hits(L, L ∪ I, order, T, k, τ)         # profile = first k sessions
    users.csv   += 09.user_rows(hit)                          # accuracy per user
    heatmap.csv += for n in 1 … |L|: impostors through with the profiles of L[:n] / |I|
summary.csv ← 09.summarize per k
```

The tested sessions do not change between steps, and step $k + 1$ contains step $k$ (nested prefix of one
shuffle), so differences come only from the extra profile session.

## Outputs in detail

- **`find_session.png`**: like 09's figure, two separate graphs (accuracy per legitimate user, accuracy per
  impostor), one line per session count.
- **`sensitivity_heatmap.png`**: rows = profile sessions, columns = number of legitimate users (the first
  1 … `n_legitimate` of the draw, as in the notebook's heatmap). Colour = **sensitivity** = impostors through /
  impostors (the former *threshold*), fixed 0–1 scale in 0.1 steps, 0 = best; each cell also shows the count.

Accuracy and sensitivity are defined in [09](09_find_sensitivity.md) [[1]](#ref-1); matching is script 04's banded
DTW [[2]](#ref-2).

## What we learned (`oct14_exp1_c8f010`)

At sensitivity 0.02, user20 vs four impostors, 1 and 2 sessions: the heatmap is 0.00 (no impostor through) and
user20's own sessions are rejected at both steps.

## Settings used

Everything 09 uses.

## References

<a id="ref-1"></a>[1] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).

<a id="ref-2"></a>[2] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).
