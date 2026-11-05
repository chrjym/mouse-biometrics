# 17_best_balanced.py — balanced best setting per hash folder and over many seeds

Reads `runs/<hash>/accuracy.csv` (notebook section 4 / script 10). Per (split, sensitivity, sessions) it adds the session
counts of every user and computes:

- `legit_accept_rate` = legitimate sessions passed / tested (TAR)
- `impostor_reject_rate` = 1 − impostor sessions passed / tested (TRR)
- `worst_side` = min(TAR, TRR): the balance score, ranked first, so a cell that rejects everyone (TAR 0) or lets everyone
  in (TRR 0) never wins, even though both give balanced accuracy 0.5
- `balanced_accuracy` = (TAR + TRR) / 2, `gap` = |TAR − TRR|, `user_balanced_accuracy` = the same at user level (`through`)
- `beats_chance` = both TAR and TRR above 0.5

- `impostor_accept_rate` = impostor sessions passed / tested (FAR)
- `qualifies` = `legit_ahead` (more legitimate than impostor sessions go through: TAR > FAR) and `legit_enough`
  (TAR >= `--min-legit`, default 0.5)

Ranking (user request 2026-11-05, replaces the first `worst_side`-first version of the same day): qualifying cells
first, then higher `balanced_accuracy`, then higher TAR, then **more sessions**, then **higher sensitivity**. A rank-1
row with `qualifies = False` means no cell of that split qualifies. A qualifying winner can still let most impostors in
(a6e6f7 1 x 5: TAR 1.00, FAR 0.97, balanced 0.515): it is only the best that exists, so read `impostor_accept_rate`.
`all`/`all` rows pool every split.

```bash
.venv/bin/python experiment_earl/src/17_best_balanced.py            # the hash config.yaml selects
.venv/bin/python experiment_earl/src/17_best_balanced.py a6e6f7 19399f
.venv/bin/python experiment_earl/src/17_best_balanced.py --all      # every runs/<hash>/ with accuracy.csv (e.g. 500 seeds)
```

Per hash: `best_balanced/best.csv` (rank 1 per split + pooled), `scores.csv`, `scores_all_splits.csv`.
With more than one hash: `runs/best_balanced_seeds.csv` (each seed's best rows, with `hash`, `seed` from the `config.yaml`
snapshots) and `runs/best_balanced_summary.csv` (every cell's mean/std/min `worst_side`, mean rates, `seeds`,
`times_best`, `seeds_qualifying`, `seeds_beating_chance`, ranked the same way on the means). The summary groups only by split, sensitivity
and sessions, so pass hashes that differ only in seed. Cells with very few tested sessions (1 session, 1 legitimate
user) can score 1.0 in one seed; look at `seeds` and `worst_side_std` before trusting a single-seed winner.
