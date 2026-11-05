# 18_plot_best_balanced.py — plot a slice of 17's ranking

Draws ranks A–B of `17_best_balanced.py`'s ranking for one experiment and split, one row per setting (best on top):
blue bar = legitimate sessions through (TN / (TN + FP)), orange bar = impostor sessions through (FN / (FN + TP)),
dark dot = the notebook's accuracy; hatched bars = not qualifying; the right column gives the counts (one hash) or
`best in b/s seeds, qualifies in q` (summary). Dotted line = 0.5.

```bash
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py a6e6f7                      # top 10, exp1, split all
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py a6e6f7 --rows 11-20
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py a6e6f7 --experiment exp2 --split "1 x 5" --rows 5
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --summary --rows 20 --qualifying-only   # over all seeds
```

- `--rows N` = ranks 1–N, `--rows A-B` = ranks A–B (stops at the last rank; error if A is past it).
- One hash: ranks = the `rank` column of `runs/<hash>/best_balanced/<exp>_scores.csv` → PNG in
  `runs/<hash>/best_balanced_plots/` (not `best_balanced/`, which 17 rewrites).
- `--summary`: `runs/best_balanced_summary.csv` in its order (times_best, seeds_qualifying, accuracy, x) →
  `runs/best_balanced_plots/`; `qualifies` there = qualifies in at least one seed.
- `--qualifying-only` drops non-qualifying rows first and renumbers the ranks. On `a6e6f7` exp 1 split `all`, only
  0.06 qualifies; ranks 2–10 are sensitivities 1.00–0.92 where every session goes through (accuracy 0.5).
- File name: `<exp>_<split without spaces>[_qualifying]_rank_<A>-<B>.png`.
