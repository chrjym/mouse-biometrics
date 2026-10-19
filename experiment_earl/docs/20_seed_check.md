# `20_seed_check.py`: do the chosen settings hold on new seeds?

[← index](README.md) · previous: [19](19_cohort_score.md)

## What it does

[18](18_pick_best.md) and [19](19_cohort_score.md) pick their best setting per split on the same runs they score, so
their numbers are optimistic. This script takes each method's choice on the hash folder's seed (the **training
seed**) and applies it **unchanged** to new seeds (the **test seeds**: a new user order and new session orders):

- **match** (18): the chosen `sensitivity` and `sessions_per_user`, scored with 16's rules (`16.score_config`).
- **raw** and **cohort** (19): the chosen sessions per user and acceptance threshold, scored with 19's rules.

Run 16 and 18 on the hash folder first (it reads `runs/<hash>/best/best.csv`).

```bash
.venv/bin/python experiment_earl/src/20_seed_check.py 251ea4                          # test seeds = seed + 1 ... + 3
.venv/bin/python experiment_earl/src/20_seed_check.py 251ea4 --test-seeds 11 22 33 44
```

`--max-sessions`, `--strokes-per-session` and `--cap` are 19's flags and must match the 19 run being checked.

Outputs, in `runs/<hash>/seed_check/`:

- `results.csv`: one row per (split, method, seed), with `role` = train or test: the setting, users through on
  each side, user and session accuracy, and the EER at the chosen sessions (19's methods only).
- `summary.csv`: per split and method, the training value next to the mean, lowest and highest test value, and the
  impostors and legitimate users through summed over the test seeds.
- `seed_check.png`: one panel per method; per split the training user accuracy (light), the test mean (dark) and
  each test seed (dots).

## Algorithm

```
training seed s0 (the hash folder's):
    match:       chosen ← runs/<hash>/best/best.csv (sensitivity, sessions per split)
    raw, cohort: claims ← 19.score_sessions(s0);  cells ← 19.score_cells
                 chosen ← per split and method, the (sessions, threshold) with the best user accuracy
for each test seed s:
    users, session orders ← the draw of s
    match:       16.score_config(seed s, split, chosen sensitivity and sessions) → users through
    raw, cohort: claims of s at the chosen sessions → users through at the chosen threshold, EER
summary: training value vs mean / min / max over the test seeds
```

## Why these choices

- **Nothing is re-tuned on a test seed.** Only the chosen setting travels. If a method's accuracy drops to chance
  on new seeds, its training number was luck from tuning; if it holds, the setting generalizes.
- **Both methods are checked the same way.** 18 also tuned its sensitivity and sessions on the training seed, so
  comparing 19's test result with 18's training result would favour 18; the training rows show both.
- **New seed = new users order and new sessions.** The legitimate users of a split change with the seed, so the
  test also asks whether a setting works for other people, not only for other sessions of the same people.
- **Several test seeds.** With 1–9 users per side one seed moves in steps of 1/9 … 1, so the mean and the spread
  over seeds say more than any single value.

## First result (`251ea4`, train seed 927, test seeds 928–930)

Mean user accuracy over the 9 splits, training seed → new seeds: 18's matching 0.63 → 0.44, 19 raw 0.70 → 0.50,
19 cohort 0.82 → 0.42. Mean EER on the new seeds: raw 0.44, cohort 0.46. No method's chosen setting stays above
chance on new seeds except in the 1–9 split (match 0.63, cohort 0.69, with one test seed at 0.28 and 0.50); cohort
falls the most, so its training gain was tuning to seed 927 (one free threshold per split and session count).
Several test values are below 0.5: a threshold set for one draw's users rejects other users' own sessions and lets
their impostors through.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
