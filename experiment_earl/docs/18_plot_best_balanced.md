# 18_plot_best_balanced.py — plot a slice of 17's ranking

Draws ranks A–B of `17_best_balanced.py`'s ranking for one experiment and split, one row per setting (best on top):
blue bar = legitimate sessions through (TN / (TN + FP)), orange bar = impostor sessions through (FN / (FN + TP)),
dark dot = the notebook's accuracy; the right column gives `best in b/s seeds, qualifies in q` (all seeds: bars and
dot are means over seeds, hatched = qualifies in no seed) or the counts (`--seed`: hatched = not qualifying).
Dotted line = 0.5. Reads `runs/best_balanced/` only, writes `runs/best_balanced/plots/`.

```bash
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py                              # all seeds, top 10, exp1, split all
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --rows 11-20
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --experiment exp2 --split "1 x 5" --rows 5
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --qualifying-only --rows 20
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --seed 946                   # one seed's ranking
```

- `--rows N` = ranks 1–N, `--rows A-B` = ranks A–B (stops at the last rank; error if A is past it).
- Ranks = the `rank` column of `summary.csv` (all seeds) or of `scores.csv` for that seed.
- `--qualifying-only` drops non-qualifying rows first and renumbers the ranks. On seed 946 exp 1 split `all`, only
  0.06 qualifies; ranks 2–10 are sensitivities 1.00–0.92 where every session goes through (accuracy 0.5).
- File name: `<all_seeds|seed_N>_<exp>_<split without spaces>[_qualifying]_rank_<A>-<B>.png`.
