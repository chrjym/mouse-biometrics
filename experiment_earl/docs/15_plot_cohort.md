# `15_plot_cohort.py`: what cohort scoring looks like

[← index](README.md) · previous: [14](14_seed_check.md) · next: [16](16_sweep_sensitivity.md)

## What it does

Draws what [13](13_cohort_score.md) computes, from 13's saved scores and the same libraries (rebuilt with
`13.build_libraries`, so the strokes shown are the ones 13 scored against). Run 13 first.

```bash
.venv/bin/python experiment_earl/src/15_plot_cohort.py 251ea4                          # first legitimate user, 13's sessions for 1–9
.venv/bin/python experiment_earl/src/15_plot_cohort.py 251ea4 --user user9 --sessions 2 --strokes 8
```

Outputs, in `runs/<hash>/cohort/plots/`:

- `claim_<user>_genuine.png`, `claim_<user>_impostor_typical.png`, `claim_<user>_impostor_top.png`: one claim each
  (the median-scoring genuine session, the median-scoring impostor session and the highest-scoring impostor session
  claiming `<user>`). Each row is one stroke of the session (black), picked evenly over the session's rank range;
  column 1 shows the nearest stroke in the claimed user's profile (blue, dashed), the other columns the nearest
  stroke in each other person's background library: **red = closer than the claimed user's** (counts against the
  claim), **grey = farther** (counts for it). The number is the DTW cost per point. The row label is the stroke's
  rank; the histogram at the bottom shows every stroke's rank and the session score (their mean).
- `scores_per_split.png`: per split, at 13's chosen sessions, every claim's cohort score (genuine above, impostor
  below) with 13's chosen threshold; claims right of the line are accepted, the EER is in the title.

The script recomputes each drawn session's score and warns if it differs from `sessions.csv`.

## Why these choices

- **Median and top claims.** The median genuine and impostor sessions show the usual case; the top impostor shows
  how the method fails. On `251ea4` (user16, 8 sessions) the top impostor is a one-stroke session of user35 that
  scores 1.00 from that single stroke; it is the only tested session with fewer than 5 strokes.
- **Strokes spread over the rank range**, not the first few: a session holds strokes that argue for and against the
  claim, and a session score near 0.5 is their average.
- **Same stroke on every cell of a row.** Only the dashed stroke changes, so the eye compares how well each
  person's library fits it.

## What the figures show on `251ea4`

Genuine and impostor sessions both hold a mix of strokes that point to the claimed user and strokes that point to
someone else, so their scores overlap: on sessions with 30+ strokes, genuine claims average 0.514 and impostor
claims 0.499. Near-straight and simple curved strokes have close matches in almost every library and land on either
side by small differences in cost.
