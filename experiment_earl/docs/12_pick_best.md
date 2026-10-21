# `12_pick_best.py`: the best sensitivity and sessions per split

[← index](README.md) · previous: [10](10_plot_accuracy.md) · next: [13](13_cohort_score.md)

## What it does

Reads `runs/<hash>/accuracy.csv` (written by [10](10_plot_accuracy.md)), scores every (split, sensitivity,
`sessions_per_user`) cell, and keeps the best cell of each split (`n_legitimate`, `n_impostor`). Run 10 first.

Outputs, in a new folder `runs/<hash>/best/` (emptied and rewritten on every run):

- `best.csv`: one row per split, the chosen sensitivity and sessions, users through on each side, `user_accuracy`,
  `session_accuracy` and `beats_chance` (user accuracy above 0.5).
- `scores.csv`: every cell with its scores, to check the ranking.
- `best_rows.csv`: the rows of `accuracy.csv` for the chosen cells only (one per user).
- `best_heatmaps.png`: one heatmap per split (y = sensitivity, x = sessions per user, colour = user accuracy,
  white = chance), the chosen cell boxed. Sensitivities above the last one where any cell differs from 0.5 are cut.
- `accuracy_<L>_<I>_sensitivity_<value>.png`: a copy of 10's figure for each chosen split and sensitivity.

## Algorithm

```
for each (split, sensitivity, sessions) in accuracy.csv:
    user_accuracy    ← (legitimate users through / legitimate users + impostors not through / impostors) / 2
    legit_accepted    ← Σ passed / Σ tested over the legitimate users
    impostor_accepted ← Σ passed / Σ tested over the impostor users
    session_accuracy ← (legit_accepted + 1 − impostor_accepted) / 2
per split: best ← highest user_accuracy; ties → higher session_accuracy, then fewer sessions, then lower sensitivity
beats_chance ← user_accuracy > 0.5
```

## Formulas

$$\text{user accuracy} = \frac{1}{2}\left(\frac{|\{u \in L : u \text{ through}\}|}{|L|}
+ \frac{|\{v \in I : v \text{ not through}\}|}{|I|}\right)$$

$$\text{session accuracy} = \frac{1}{2}\left(\frac{\sum_{u \in L} \text{passed}_u}{\sum_{u \in L} \text{tested}_u}
+ 1 - \frac{\sum_{v \in I} \text{passed}_v}{\sum_{v \in I} \text{tested}_v}\right)$$

Both are $1 - \text{HTER}$ with HTER $= (\text{FAR} + \text{FRR})/2$: user accuracy counts users (a user is through
at `match_session_ratio` of their sessions), session accuracy counts sessions.

## Why these choices

- **User accuracy ranks:** it is the group's 2026-10-14 rule (the mean of legitimate accuracy and impostor
  accuracy, both over users; see the adviser log), and it reads directly as "5 of 5 users accepted, 3 of 5
  impostors got in".
- **Session accuracy breaks ties and is reported next to it:** with 1–9 users per side the user rate moves in big
  steps and ties often (3 tied best cells in 1–9, 719 in 8–2). It is also stricter: a user is through at half their
  sessions, so on `251ea4` (splits 1–9 … 6–4) user accuracy is 0.67–0.71 where session accuracy is 0.55–0.65 for the same cells.
- **Balanced, not plain accuracy:** splits have 1–9 legitimate and 9–1 impostor users, so plain accuracy
  rewards rejecting everyone when impostors dominate. Both scores weigh the two sides equally, and accepting
  or rejecting everyone both score exactly 0.5.
- **Then fewer sessions and the stricter sensitivity:** the cheaper profile and the tighter match win when both
  scores are equal.
- **`beats_chance`:** a split whose best is 0.5 has no useful setting; on `251ea4` the 8–2 and 9–1 splits'
  "best" is 0.01 / 2 sessions, where nobody goes through.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
