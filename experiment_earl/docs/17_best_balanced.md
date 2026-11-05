# 17_best_balanced.py — best sensitivity and sessions from experiments 1 and 2, per seed and over many seeds

Reads `runs/<hash>/experiments/exp1_points.csv` and `exp2_points.csv` (notebook section 9), not `accuracy.csv`
(user request 2026-11-05: the best must follow the experiments' findings; the batch's `accuracy.csv` is a different
test with many sessions per user and gave 0.04 / 0.05 where experiment 1 gives 0.06 for seed 946).

Counts are the notebook's (positive = impostor): TP impostor rejected, FN impostor let in, TN legitimate accepted,
FP legitimate blocked. Each point uses its **own** counts, not the running totals the figures plot. Per split and
point, plus split `all` = every split added (= `<exp>_overall.csv`):

- `legit_through` = TN / (TN + FP), `impostor_through` = FN / (FN + TP)
- `accuracy` = (TP + TN) / all, the notebook's accuracy; `balanced_accuracy` = (legit_through + 1 − impostor_through) / 2
- `qualifies` = `legit_through > impostor_through` (more legitimate than impostor sessions go through) and
  `legit_through >= --min-legit` (default 0.5)
- `notebook_best` = the notebook's own pick (highest accuracy, ties to the lower x)

Ranking per split: qualifying first, then higher accuracy, higher `legit_through`, then **higher sensitivity** (exp 1) /
**more sessions** (exp 2). A rank-1 row with `qualifies = False` means nothing in that split qualifies.
Per-split points hold only 5–6 sessions (one per user), so single-seed per-split picks are noisy; use `all` or the
summary over seeds.

```bash
.venv/bin/python experiment_earl/src/17_best_balanced.py            # the hash config.yaml selects
.venv/bin/python experiment_earl/src/17_best_balanced.py a6e6f7 19399f
.venv/bin/python experiment_earl/src/17_best_balanced.py --all      # every runs/<hash>/ with experiments/ (e.g. 500 seeds)
```

Per hash: `best_balanced/best.csv` (rank 1 of each split, both experiments), `exp1_scores.csv`, `exp2_scores.csv`
(folder rewritten each call). With more than one hash: `runs/best_balanced_seeds.csv` (every seed's rank-1 rows, with
`hash` and `seed` from the `config.yaml` snapshots) and `runs/best_balanced_summary.csv` (per experiment, split and
point: `seeds`, mean `accuracy`/rates, `times_best` = seeds where it is rank 1 **and** qualifies, `seeds_qualifying`,
`times_notebook_best`). Experiment 2 is grouped by sessions only, since its sensitivity is each seed's own
experiment-1 best. Pass hashes that differ only in seed.

Checked 2026-11-05: on `a6e6f7` (seed 946) the `all` row gives 0.06 (TN 6 / FP 5, FN 1 / TP 10, accuracy 0.727), the
same as `exp1_overall.csv` and `exp1.png`; experiment 2 at 0.06 has no qualifying session count (every impostor session
goes through from 5 sessions on).
