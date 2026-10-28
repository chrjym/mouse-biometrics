# `17_passed_strokes.py`: passed sessions at the best setting, strokes trimmed and plotted from (0,0)

[← index](README.md)

## What it does

For every split's best setting (`runs/<hash>/best/best_rows.csv`, from the notebook's section 5), finds **which
sessions** were tested and which of them **passed**, then trims every stroke of the passed sessions to its first
`--window` seconds (default 0.5) and plots them from (0,0). The notebook saves only counts per user; this script
recovers the session IDs behind those counts.

```bash
.venv/bin/python experiment_earl/src/17_passed_strokes.py --hash 19399f [--window 0.5]
```

Needs a finished notebook run in `runs/<hash>/`: `best/` (section 5) and `strokes/` (section 10).

Output: `runs/<hash>/passed_strokes_<window>s/`

```
session_results.csv            every tested session: split, user, profile, position, session, matched, strokes, passed
summary.csv                    one row per split and user: passed sessions, strokes
<split>/<user>/
    trimmed/<session>_points_<window>s.csv   points within the first <window> s of each stroke
    first_strokes.csv          first stroke of each passed session: points, end Δx/Δy, strokes and points per session
    all_strokes_<window>s.png  every trimmed stroke of the passed sessions from (0,0)
    first_stroke_<window>s.png first stroke of each passed session from (0,0), end labelled with its position
```

## Algorithm

```
code ← the notebook's cells up to matched_chunks (same draw, chunking, DTW and cache as the run)
for each row of best_rows.csv (one user at one split's best sensitivity and sessions k):
    order ← draw_users(run config, seed)            the seed's session order per user
    library ← profile user's first k sessions
    tested ← legitimate: own last k sessions; impostor: first k sessions
    per tested session: passed ← matched strokes / strokes >= match_shape_ratio
    check: passed sessions == best_rows.passed, else stop
for each split and user with passed sessions:
    per session: points of strokes/<user>/<session>_points.csv with t − t_start(stroke) <= window
    plot every trimmed stroke, and each session's first stroke, shifted so it starts at (0,0)
```

## Choices

- **Notebook code, not `src/`.** The notebook is the simulation (adviser, 2026-10-26) and differs from the older
  scripts, so the script runs the notebook's own functions to pick and score sessions. The pass counts are checked
  against `best_rows.csv`; any difference stops the script.
- **Trim, not filter.** Every stroke is kept and cut to its first `--window` seconds. The 0.5 s `pause_gap_s` only
  decides where a stroke ends (a pause over 0.5 s, or a click); strokes themselves last 1.15 s at the median.
- **Trimmed strokes are not rescored.** Pass/fail comes from the full strokes, as in the run.
- **Sampling rate shows.** Users logged every ~110 ms (e.g. user29) keep about 5 points per 0.5 s stroke, drawn as
  straight pieces; user9 and user20 (~16 ms) keep about 30.
