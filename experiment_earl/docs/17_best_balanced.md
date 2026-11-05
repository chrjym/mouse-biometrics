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
.venv/bin/python experiment_earl/src/17_best_balanced.py                 # every runs/<hash>/ with experiments/ (every seed)
.venv/bin/python experiment_earl/src/17_best_balanced.py a6e6f7 19399f   # only these hash folders
```

Everything goes to **`runs/best_balanced/`** (user request 2026-11-05: one result for many seeds, nothing written into
the hash folders; the file is rewritten on each call):

- **`exp1_ranking.csv`, `exp2_ranking.csv`**: one ranking per experiment, all splits added, sorted best to worst
  (`rank` 1, 2, 3, ... top to bottom; user request 2026-11-05). Order: `times_best` = seeds where it is rank 1 **and**
  qualifies, then `seeds_qualifying`, then mean `accuracy`, then the higher sensitivity / more sessions. Also `seeds`,
  mean `legit_through` / `impostor_through` / `balanced_accuracy`, `accuracy_std`, `times_notebook_best`,
  `qualifies` = qualifies in at least one seed. Experiment 2 is ranked by sessions only, since its sensitivity is
  each seed's own experiment-1 best.
- `by_split/<exp>_<split>_ranking.csv` (e.g. `exp1_1x5_ranking.csv`): the same ranking for one split.
- `seeds.csv`: every seed's rank-1 row per experiment and split (with `seed`, `hash` from the `config.yaml` snapshots).
- `scores.csv`: every ranked point of every seed (what `18_plot_best_balanced.py --seed` reads), sorted by experiment, seed, split, rank.

Old `.csv` files in `runs/best_balanced/` are removed on each call; `plots/` is kept.

Pass hash folders that differ only in seed.

Checked 2026-11-05: on `a6e6f7` (seed 946) the `all` row gives 0.06 (TN 6 / FP 5, FN 1 / TP 10, accuracy 0.727), the
same as `exp1_overall.csv` and `exp1.png`; experiment 2 at 0.06 has no qualifying session count (every impostor session
goes through from 5 sessions on).
