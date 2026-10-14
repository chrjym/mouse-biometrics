# `09_find_sensitivity.py`: find the sensitivity (User × User × Sensitivity)

[← index](README.md) · next: [10](10_find_session.md)

## What it does

First step of the adviser's pipeline (2026-10-14):

```
raw → RNG (legitimate users, impostor users, sessions) → strokes (chunk shapes)
    → user × user × sensitivity (09) → user × session × sensitivity (10) → sensitivity → heatmap (10)
```

One draw from `seed` picks `n_users` users in random order and fixes each user's session order. Experiment
**E_k** takes the first $k$ users as legitimate and the other $n - k$ as their **direct-opposite impostors**:
with $n = 5$, E1 = 1 + 4, E2 = 2 + 3, E3 = 3 + 2, E4 = 4 + 1. Every E_k is scored at each **sensitivity**
in `sensitivity_values`. The sensitivity is the DTW setting `dtw_tolerance` (script 04); matching uses DTW only.

Outputs: `runs/<run>/results/sensitivity/experiments.csv`, `results/sensitivity/chosen.csv`,
`figures/find_sensitivity.png`.

## Algorithm

```
users, order ← random.Random(seed).sample(all users, n_users), each user's shuffled session pool
P ← sensitivity_sessions                                    # profile size
T[u] ← order[u][max(session_values) : max(session_values) + test_sessions]   # never in any profile
for each sensitivity τ in sensitivity_values:
    for each pair (profile p, user u) of the drawn users:   # computed once, shared by all E_k
        library ← p's first P sessions
        through[p, u] ← share of T[u] with r ≥ match_shape_ratio  is  ≥ match_session_ratio
    for k in 1 … n − 1:
        L ← users[:k],  I ← users[k:]
        legit accuracy    ← |{u ∈ L : through[u, u]}| / |L|
        impostor accuracy ← |{v ∈ I : no p ∈ L has through[p, v]}| / |I|
chosen[E_k] ← τ with the highest mean of the two accuracies (ties: the smaller, stricter τ)
```

$r$ is script 04's session match ratio: the share of a session's strokes with a DTW match (same kind, within
$\tau \cdot$ `resample_n`) in any library session.

## Formulas

$$\text{Acc}_L(E_k, \tau) = \frac{|\{u \in L : u \text{ goes through its own profile}\}|}{k},\qquad
\text{Acc}_I(E_k, \tau) = 1 - \frac{|\{v \in I : \exists\, p \in L,\ v \text{ goes through } p\}|}{n - k}$$

$$\text{Acc}(E_k, \tau) = \tfrac12\left(\text{Acc}_L + \text{Acc}_I\right),\qquad
\tau^*(E_k) = \arg\max_\tau \text{Acc}(E_k, \tau)$$

$1 - \text{Acc}_L$ is a user-level false rejection rate and $1 - \text{Acc}_I$ a user-level false acceptance
rate [[1]](#ref-1); the mean of both is balanced accuracy, so E1 (1 legitimate, 4 impostors) and E4 (4, 1) weigh
both sides equally. The CSV also stores $1 - \text{Acc}_I$ as `impostor_sensitivity`: the old *threshold*
(impostors through / impostors), renamed by the adviser.

## Why these choices

- **Direct opposite:** every drawn user is either legitimate or impostor in each E_k, so the impostor set is
  exactly the complement and the experiments differ only in where the split falls.
- **One draw:** the same users and sessions in every E_k and every sensitivity, so differences come from the
  split and the tolerance, not from a new random draw.
- **Fixed tested sessions** after the largest profile (also 10's `session_values`), so 09 and 10 test the same
  sessions and a legitimate user's tested sessions are never part of their own profile.
- **Two separate graphs** (adviser): legitimate accuracy against the number of legitimate users, impostor
  accuracy against the number of impostor users, one line per sensitivity.

## What we learned (`oct14_test1_229cd4`, users user21, user15, user29, user23, user12)

At every sensitivity from 0.2 to 1.0 every legitimate user is accepted and every impostor goes through
(legitimate accuracy 1, impostor accuracy 0, mean 0.5), so all lines overlap and 0.2 is chosen by the tie rule.
DTW with banding [[2]](#ref-2) on normalized strokes is already permissive at 0.15 (about 99% of strokes match).
A probe outside the config at 2 sessions gave: 0.01–0.02 nobody goes through (mean 0.5), 0.03 one legitimate
user accepted and no impostor through (E3 0.67, E4 0.63), 0.05 impostors start going through, 0.1 everyone again.

## Settings used

`seed`, `n_users`, `sensitivity_values`, `sensitivity_sessions`, `session_values`, `test_sessions`, the chunking
settings, `dtw_band`, `match_shape_ratio`, `match_session_ratio`.

## References

<a id="ref-1"></a>[1] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).

<a id="ref-2"></a>[2] H. Sakoe and S. Chiba, "Dynamic programming algorithm optimization for spoken word recognition," *IEEE Trans. Acoust., Speech, Signal Process.*, vol. 26, no. 1, pp. 43–49, Feb. 1978, doi: [10.1109/TASSP.1978.1163055](https://doi.org/10.1109/TASSP.1978.1163055).
