# `05_threshold.py`: the threshold of a trial

[← index](README.md) · previous: [04](04_match_shapes.md) · next: [06](06_sweep.md)

## What it does

Step 5, the last step of the single trial. It reads every `results/trial_*.json` of the run, computes one number
per trial (the **threshold**), and writes `results/summary.csv`.

## Formula

$$\text{threshold} = \frac{\text{matched\_detected}}{\text{total\_impostor\_users}} = \frac{|\{ v \in I : v \text{ matched} \}|}{|I|}$$

"Matched" is the decision of script 04: some legitimate profile accepted at least `match_session_ratio` of the
impostor's sessions.

## How to read it

- **0** = no impostor got through any profile (best).
- **1** = every impostor got through (worst).

It is the share of impostor **users** wrongly accepted, i.e. a user-level false acceptance rate. It is
called "threshold" because Earl's plan (and the whiteboard sketch `image.png`) uses that name. It is the value
drawn on the 0–1 heatmap.

## Why a share and not a count

Dividing by the number of impostors puts trials with 1, 2 or 4 impostors on the same 0–1 scale, so they can be
compared and averaged. As a result, the threshold barely changes with the number of impostors in the sweep (06).

## Algorithm

```
for every trial_*.json (in trial-number order):
    detected  ← number of records with matched = true
    threshold ← detected / n_impostor
write one row (trial, n_legit, n_sessions, n_impostor, matched_detected, threshold)
```

## Output

`runs/<run>/results/summary.csv`.
