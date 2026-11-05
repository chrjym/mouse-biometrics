# 18_plot_best_balanced.py — plot ranks A–B of the per-seed best

Reads `runs/best_balanced/best_per_seed.csv` (script 17) and draws the seeds of ranks A–B, one row per seed (rank 1 on
top): label `#rank seed N sensitivity s`; blue bar = legitimate sessions through, orange bar = impostor sessions through,
dark dot = accuracy; right column = accuracy and counts (`legit 6/11, impostor 1/11`); hatched + "(legitimate rule not
met)" = `legit_ahead` is false. Dotted line = 0.5.

```bash
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py              # ranks 1-10
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --rows 11-20
.venv/bin/python experiment_earl/src/18_plot_best_balanced.py --rows 21-30
```

`--rows N` = ranks 1–N, `--rows A-B` = ranks A–B (stops at the last seed; error if A is past it).
Output: `runs/best_balanced/plots/best_per_seed_rank_<A>-<B>.png`.
