# `10_find_session.py`: find the sessions (User × Session × Sensitivity) and the heatmap

[← index](README.md) · previous: [09](09_find_sensitivity.md)

## What it does

Second and last step of the adviser's pipeline (2026-10-14). It uses the same draw and experiments E1 … E(n − 1)
as script 09 and, for each E_k, the sensitivity 09 chose for it (`results/sensitivity/chosen.csv`, so run 09
first). Each E_k is then scored with 2, 4, … 10 profile sessions per legitimate user (`session_values`).

Outputs: `runs/<run>/results/session/experiments.csv`, `figures/find_session.png`,
`figures/sensitivity_heatmap.png`.

## Algorithm

```
users, order ← 09.draw(config, seed)                # the same users and session orders as 09
τ*[E_k]       ← chosen.csv
for k_s in session_values:
    for each distinct τ in τ*:
        through ← 09.pass_matrix(users, order, k_s, τ)     # profile = first k_s sessions
        keep the rows of 09.score(...) for the E_k whose τ*[E_k] = τ
```

The tested sessions are the same as in 09 (`test_sessions` after `max(session_values)`), so only the profile
grows between steps, and step $k_s + 2$ contains step $k_s$ (nested prefix of one shuffle).

## Outputs in detail

- **`find_session.png`**: like 09's figure, two separate graphs (legitimate accuracy against the number of
  legitimate users, impostor accuracy against the number of impostors), one line per session count.
- **`sensitivity_heatmap.png`**: rows = profile sessions, columns = E_k (with L, I and the chosen τ). Colour =
  **sensitivity** = impostors through / impostors (the former *threshold*), fixed 0–1 scale in 0.1 steps,
  0 = best. Each cell also shows impostors through and legitimate users accepted.

Accuracy and sensitivity are defined in [09](09_find_sensitivity.md) [[1]](#ref-1); matching is script 04's banded
DTW [[2]](#ref-2).

## What we learned (`oct14_test1_229cd4`)

With τ* = 0.2 for every E_k (see 09), every session count from 2 to 10 gives legitimate accuracy 1 and impostor
accuracy 0: the heatmap is 1.0 in every cell. More sessions cannot help when the tolerance already lets every
stroke match.

## Settings used

Everything 09 uses, plus `session_values`.

## References

<a id="ref-1"></a>[1] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).

<a id="ref-2"></a>[2] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).
