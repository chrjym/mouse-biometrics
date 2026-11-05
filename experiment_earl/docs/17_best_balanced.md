# 17_best_balanced.py — one best sensitivity per seed, seeds ranked by accuracy

User request 2026-11-05: for many seeds (pulled with `server/pull_runs.py`), record **only each seed's single best**:
its best sensitivity and that accuracy, as experiment 1 found it, and rank the seeds.

For every `runs/<hash>/` with `experiments/` (one hash per seed), it reads the notebook's own pick, the `best = True` row
of `experiments/exp1_overall.csv` (all splits added; highest accuracy, ties to the lower sensitivity), the same value
as the title of `exp1.png`, and of `exp2_overall.csv` (best sessions at that sensitivity). Nothing is re-ranked inside a
seed. (An earlier version of the same day picked its own best with a "legitimate must win" rule and disagreed with
the figures on seeds 945 and 989; dropped.)

Counts (positive = impostor): TP impostor rejected, FN impostor let in, TN legitimate accepted, FP legitimate blocked.

`runs/best_balanced/best_per_seed.csv`, one row per seed, sorted by `accuracy` highest first (ties: higher
sensitivity), `rank` 1, 2, 3, ... top to bottom:

| Column | Meaning |
|---|---|
| `rank`, `seed`, `hash` | place in the ranking, seed (from the `config.yaml` snapshots), hash folder |
| `sensitivity`, `accuracy` | experiment 1's best sensitivity and its accuracy |
| `legit_through`, `impostor_through` | TN / (TN + FP), FN / (FN + TP) at that sensitivity |
| `TP`, `FP`, `FN`, `TN` | its counts |
| `legit_ahead` | `legit_through > impostor_through` and `legit_through >= --min-legit` (default 0.5); a check only |
| `exp2_sessions`, `exp2_accuracy`, `exp2_legit_through`, `exp2_impostor_through`, `exp2_legit_ahead` | experiment 2's best |

Other `.csv` files in `runs/best_balanced/` are removed on each call; `plots/` is kept.

```bash
.venv/bin/python experiment_earl/src/17_best_balanced.py                 # every seed in runs/
.venv/bin/python experiment_earl/src/17_best_balanced.py a6e6f7 19399f   # only these hash folders
```

Checked 2026-11-05 on the 3 local seeds: 946 → 0.06 (0.727), 945 → 0.05 (0.727), 989 → 0.01 (0.500), equal to each
`exp1_overall.csv`.
