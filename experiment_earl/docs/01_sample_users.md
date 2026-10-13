# `01_sample_users.py`: draw the legitimate and impostor users

[← index](README.md) · next: [02](02_sample_sessions.md)

## What it does

Step 1 of the single file-based trial (01 → 05). It randomly picks which Balabit users act as **legitimate**
users (their strokes form the profiles) and which act as **impostors** (their strokes are tested against the
profiles). It writes the choice to `runs/<run>/temp/manifest.json`.

Scripts 10, 11, 12 and 13 also call its `draw_users()` to choose the users of their headline row, so all methods
are scored on the same people.

## Algorithm: seeded sampling without replacement

```
users      ← the 10 Balabit users, sorted by name
rng        ← Random(seed)
legitimate ← rng.sample(users, n_legitimate)              # no repeats
remaining  ← users that are not legitimate
impostor   ← rng.sample(remaining, n_impostor)            # no repeats, never a legitimate user
return sorted(legitimate), sorted(impostor)
```

`random.sample` picks without replacement: each user is chosen at most once, and every subset of size *n* is
equally likely.

## Constraint

$$n_\text{legitimate} + n_\text{impostor} \le 10$$

Balabit has only 10 users, and a user cannot be both legitimate and impostor in the same run. This is why the
original plan's 5/10/15/20 impostors cannot be done here. The script stops with an error when the sum is too large.

## Why random, and why seeded

- **Random:** if we always used the same users, a result could depend on one lucky or unlucky pair of users.
  Drawing at random, and redrawing with a different seed, shows whether the result holds for other users too.
- **Seeded:** the same `seed` always gives the same users, so the group and the adviser can rerun and check a figure.
- **One draw per run (user decision, 2026-10-12):** once the seed picks the users, they stay fixed for the whole
  run. Every step and every figure is then about the same people.

Script 14's `draw_users` makes the same two `sample` calls with the same generator, so it picks the **same
sets**. It keeps the legitimate users in draw order instead of sorting them; this matters only for the
notebook's heatmap columns.

## Input / output

- Input: `config.yaml` (`seed`, `n_legitimate`, `n_impostor`); `--seed` overrides the seed.
- Output: `runs/<run>/temp/manifest.json` = `{"seed", "legitimate", "impostor"}`.
