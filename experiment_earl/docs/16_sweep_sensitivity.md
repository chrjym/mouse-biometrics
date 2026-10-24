# `16_sweep_sensitivity.py`: sensitivity × library size for fixed splits, one confusion matrix per setting

[← index](README.md) · previous: [15](15_plot_cohort.md) · next: [17](17_plot_sweep.md)

## What it does

For every split in `splits` of `config.yaml` (fixed: 1 vs 5, 5 vs 1, 3 vs 2, 2 vs 3), every library size
k = 1 … `sweep_sessions_max` and every sensitivity of `sweep_sensitivity` (start, stop, step), it decides for each
test session whether it is accepted and counts the outcomes into one confusion matrix per setting. With the
defaults that is 4 × 40 × 100 = 16,000 settings.

Outputs, in `runs/<hash>/sweep/` (emptied and rewritten on every run; the sweep keys are left out of the hash, so
a new grid overwrites the old one):

- `confusion.csv`: one row per (split, `sessions`, `sensitivity`) with `tp`, `fp`, `fn`, `tn`, `far`, `frr`,
  `balanced_accuracy` and plain `accuracy`.
- `best.csv`: the best row of each split, plus `eer`.
- `splits.csv`: the users drawn for each split and how many test sessions each side has.
- `config.yaml`: the settings the sweep used.

Run [17](17_plot_sweep.md) afterwards for the figures.

## The draw: fixed splits, random users

The split sizes come from `config.yaml` and never change. For each split a **fresh** `random.Random(seed)` draws
the users exactly as the notebook does (`08.draw_users`): `n_legitimate` legitimate users, then `n_impostor`
impostors from the rest. So the users depend on the seed, each split is its own draw, and the same user can be
legitimate in one split and an impostor in another. Each user's sessions are in their `session_pool` order
(shuffled once by `seed`), as in every other script.

## Algorithm

```
for each split [L, I]:
    legit, impostors ← draw from Random(seed)
    library(u, k)    ← first k sessions of u's pool, k = 1 … K           (K = sweep_sessions_max)
    test(u)          ← last T sessions of u's pool if u is legitimate    (T = sweep_test_sessions, never in a library)
                       first T sessions of u's pool if u is an impostor
    for each test session q and each library session j of a legitimate user u:
        d[q, j, stroke] ← nearest banded-DTW cost per point from the stroke to any stroke of session j (same kind)
    D[q, u, k, stroke] ← min over j ≤ k of d[q, j, stroke]               (running minimum: library of k sessions)
    pass(q, u, k, s)   ← #{strokes with D ≤ s} / strokes of q ≥ match_shape_ratio
    legitimate q of u: accepted(k, s) ← pass(q, u, k, s)
    impostor q:        accepted(k, s) ← any legitimate u with pass(q, u, k, s)
    for each (k, s):   count TP, FP, FN, TN over all test sessions of the split
```

DTW runs once per (test session, library session) pair, through 13's `library_nearest` and its cache
(`cache/nearest.pkl`). The cost is capped one grid step above the largest sensitivity, so a capped stroke never
matches. Every sensitivity is then only a cut on the saved distances, and every library size a running minimum.

## Is anything appended?

No. Each (split, library size, sensitivity) row is counted from scratch over every test session of that split:
nothing carries over from one iteration to the next. Library sizes are nested (the library of k + 1 sessions
contains the library of k), so a larger library can only accept more sessions, but that comes from the running
minimum over the same distances, not from adding to earlier counts. `confusion.csv` is written once at the end and
replaced on every run.

## Formulas

Positive = impostor:

| | actually impostor | actually legitimate |
|---|---|---|
| rejected | TP | FP |
| accepted | FN | TN |

$$\mathrm{FAR} = \frac{FN}{TP + FN} \qquad \mathrm{FRR} = \frac{FP}{FP + TN} \qquad
\text{balanced accuracy} = 1 - \frac{\mathrm{FAR} + \mathrm{FRR}}{2}$$

TP + FN = impostors × T and FP + TN = legitimate users × T. EER is taken along the sensitivity grid at the best
library size: the mean of FAR and FRR where they are closest.

## Why these choices

- **Balanced accuracy ranks, not plain accuracy:** in 1 vs 5 the test set is 1 × 40 legitimate and 5 × 40
  impostor sessions, so rejecting everyone already scores 0.83 plain accuracy. Accepting or rejecting everyone
  both give exactly 0.5 balanced accuracy. Ties go to fewer sessions, then the lower sensitivity.
- **Legitimate tests are the last sessions, impostor tests the first:** the same rule as
  [10](10_plot_accuracy.md); with pools of at least 114 sessions and K + T = 80, a legitimate test session is never
  in that user's library.
- **Any library accepts an impostor:** as in the notebook and 10, an impostor gets in when one legitimate profile
  accepts them. With several legitimate users this favours impostors.

## First result (`526e7a`, seed 945, 2026-10-24)

About 3 minutes the first time, 12 seconds with a warm cache.

| Split | Legitimate | Impostors | Best | TP | FP | FN | TN | Balanced accuracy | EER |
|---|---|---|---|---|---|---|---|---|---|
| 1 vs 5 | user29 | user9, 15, 20, 23, 35 | 0.05, 2 sessions | 166 | 25 | 34 | 15 | 0.602 | 0.405 |
| 5 vs 1 | user9, 15, 20, 23, 29 | user16 | 0.02, 9 sessions | 39 | 174 | 1 | 26 | 0.552 | 0.558 |
| 3 vs 2 | user20, 23, 29 | user9, 15 | 0.02, 5 sessions | 77 | 114 | 3 | 6 | 0.506 | 0.596 |
| 2 vs 3 | user23, 29 | user7, 15, 20 | 0.11, 2 sessions | 1 | 0 | 119 | 80 | 0.504 | 0.585 |

In 2 vs 3, 11 cells tie exactly at 0.504 (for example 0.04 / 10 sessions: TP 10, FP 6, FN 110, TN 74); the
tie-break picks the fewest sessions. Above sensitivity 0.44 every setting is 0.5. No setting keeps both FAR and FRR
low: every best cell buys its score by rejecting almost everyone or accepting almost everyone.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and [13_cohort_score.md](13_cohort_score.md) for
the nearest-cost function this script reuses.
