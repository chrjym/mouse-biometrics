# `18_pick_best.py`: the best sensitivity and sessions per split

[← index](README.md) · previous: [16](16_plot_accuracy.md)

## What it does

Reads `runs/<hash>/accuracy.csv` (written by [16](16_plot_accuracy.md)), scores every (split, sensitivity,
`sessions_per_user`) cell, and keeps the best cell of each split (`n_legitimate`, `n_impostor`). Run 16 first.

Outputs, in a new folder `runs/<hash>/best/` (emptied and rewritten on every run):

- `best.csv`: one row per split, the chosen sensitivity and sessions with their scores, and `beats_chance`.
- `scores.csv`: every cell with its scores, to check the ranking.
- `best_rows.csv`: the rows of `accuracy.csv` for the chosen cells only (one per user).
- `best_heatmaps.png`: one heatmap per split (y = sensitivity, x = sessions per user, colour = balanced accuracy,
  white = chance), the chosen cell boxed. Sensitivities above the last one where any cell differs from 0.5 are cut.
- `accuracy_<L>_<I>_sensitivity_<value>.png`: a copy of 16's figure for each chosen split and sensitivity.

## Algorithm

```
for each (split, sensitivity, sessions) in accuracy.csv:
    legit_accepted    ← Σ passed / Σ tested over the legitimate users
    impostor_accepted ← Σ passed / Σ tested over the impostor users
    balanced_accuracy ← (legit_accepted + 1 − impostor_accepted) / 2
per split: best ← highest balanced_accuracy; ties → fewer sessions, then the lower sensitivity
beats_chance ← balanced_accuracy > 0.5
```

## Formulas

$$\text{BA} = \frac{1}{2}\left(\frac{\sum_{u \in L} \text{passed}_u}{\sum_{u \in L} \text{tested}_u}
+ 1 - \frac{\sum_{v \in I} \text{passed}_v}{\sum_{v \in I} \text{tested}_v}\right)$$

This is $1 - \text{HTER}$ with HTER $= (\text{FAR} + \text{FRR})/2$ at the session level, where FAR is the share
of impostor sessions accepted and FRR the share of legitimate sessions rejected.

## Why these choices

- **Balanced accuracy, not plain accuracy:** splits have 1–9 legitimate and 9–1 impostor users, so plain accuracy
  rewards rejecting everyone when impostors dominate. Balanced accuracy weighs both sides equally, and accepting
  or rejecting everyone both score exactly 0.5.
- **Sessions, not users:** a user goes through or not, so with 1–9 users per side the user-level rate moves in
  big steps and ties often; session counts are finer. `best.csv` still lists users through on each side.
- **Ties to fewer sessions and the stricter sensitivity:** the cheaper profile and the tighter match win when they
  score the same.
- **`beats_chance`:** a split whose best is 0.5 has no useful setting; on `251ea4` the 8–2 and 9–1 splits'
  "best" is 0.01 / 2 sessions, where nobody goes through.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
