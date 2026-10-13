# `15_genuine_check.py`: does the user's own unseen data match their profile?

[← index](README.md) · previous: [14](14_plot_matches.md)

## What it does

The notebook measures only one side of the problem: how many **impostors** get through. A useful profile must
also accept its **owner**. This script takes the same draw and the same profiles as the notebook and scores, for
each legitimate user and each step $k$:

- **genuine:** the user's next `--held-out` sessions (default 2), which come after the first
  `sessions_per_user` sessions and are therefore **never** in the profile;
- **impostor:** the impostors' first $k$ sessions (exactly what the notebook tests).

Outputs: `runs/<run>/results/genuine_check.csv`, `results/genuine_check_summary.csv`, `figures/genuine_check.png`.

## Algorithm

```
legitimate, impostors, order ← 14.draw_users(config, seed)          # the notebook's draw
held_out[u] ← order[u][sessions_per_user : sessions_per_user + held_out]
for each legitimate user u, for k in 1 … sessions_per_user:
    library ← u's first k sessions
    for each held-out session of u:           score as "genuine"
    for each impostor v, each of v's first k: score as "impostor"
score(session) = r = matched_chunks(session, library) / strokes(session)      # 04's ratio, shared DTW cache
passed         = r ≥ match_shape_ratio
```

Summary per (user, $k$, kind): the mean ratio $\bar r$, and *passed / tested*.

## Formulas

$$r_s = \frac{|\{\text{strokes of } s \text{ with a DTW match in the library}\}|}{|\{\text{strokes of } s\}|},
\qquad \text{passed}(s) = \mathbb{1}[r_s \ge \sigma]$$

A useful profile needs

$$\bar r_\text{genuine} > \bar r_\text{impostor} \quad\text{and}\quad \text{genuine sessions pass while impostors do not.}$$

## Why held-out sessions taken this way

- **No leakage:** a session that is already in the library would match itself perfectly. Using the sessions
  *after* the first `sessions_per_user` ones guarantees that no step's library ever contains them.
- **Same sessions at every step:** the genuine test set is fixed, so changes across $k$ come only from the growing
  library.
- **Same cache:** the matching is identical to 04's (`matched_chunks`, shared `pairs.pkl`), so the numbers can be
  compared directly with the notebook's.

## Figure

One panel per legitimate user. Blue bars show the genuine mean ratio and red bars the impostor mean ratio, per
$k$. The labels give *passed / tested*, and a dotted line marks `match_shape_ratio`. The panel title says whether
the held-out sessions are training or test files: test files can be very short.

## What we learned (`oct12_test3_d05fb2`, impostors user16 + user21)

- Own sessions pass only for user9 and user20 (2/2 from 1–2 sessions, 35–57% of strokes matched), and for user29
  at 4–5 sessions (1/2).
- user12, user15 and user35 never pass (11–21% of strokes matched).
- The own share beats the impostors' share for 5 of 6 users, but user9 and user20 are also the users who get
  through **as impostors**. Passing therefore tracks a user's tendency to draw straight strokes more than their
  identity.
- user15's and user35's held-out sessions include short test files (44–61 strokes).
