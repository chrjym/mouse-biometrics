# `16_sweep_sensitivity.py` and `17_plot_sweep.py`: the sensitivity sweep

[← index](README.md)

## What it does

Tests every sensitivity from 0.01 to 1.00 (step 0.01) at every library size 1 … 40 sessions, for the four
I × L mixes 1 × 5, 5 × 1, 2 × 3 and 3 × 2, and fills one confusion matrix per (split, sessions, sensitivity).
Settings are in [`sweep.yaml`](../sweep.yaml) (`seed`, `splits`, `sensitivity` as start/stop/step, `max_sessions`);
chunking, `dtw_band`, `match_shape_ratio` and `match_session_ratio` come from `config.yaml`.

Outputs, in `runs/<hash>/sweep/` (hash = `config.yaml` with sweep.yaml's seed):

- 16: `confusion.csv` (one row per split × sessions × sensitivity: TP, FP, FN, TN, accuracy, FAR, FRR,
  balanced accuracy, the same matrix counted per user, and the users drawn), `parts/<L>_<I>.csv` (one per split;
  a rerun reuses finished splits, delete `parts/` to recompute) and a copy of `sweep.yaml`.
- 17: `best.csv` (per split: highest balanced accuracy, ties → lower sensitivity, then fewer sessions; plus the EER and its
  sensitivity), `accuracy_vs_sensitivity.png` (one line per split, panels at 1, m/4, m/2, m sessions),
  `accuracy_heatmap.png` (sessions × sensitivity per split, colour = balanced accuracy: white = 0.5 chance, blue = better, red = worse, as 12; star = best), `far_frr.png` (FAR and FRR at each
  split's best session count) and `confusion_best.png` (the 2 × 2 matrix at each best setting).

## Confusion matrix (positive = impostor)

|                 | actual I | actual L |
|-----------------|----------|----------|
| **predicted I** (rejected) | TP | FP |
| **predicted L** (accepted) | FN | TN |

One count per legitimate test session and per impostor (session, library) attempt, so impostors get one chance per
attempt like legitimate sessions. Accuracy = (TP + TN) / all attempts; FAR = FN / impostor attempts;
FRR = FP / legitimate sessions. With unequal mixes (1 I × 5 L) accuracy rewards accepting everyone, so 17 picks the best
setting by `balanced_accuracy` = 1 − (FAR + FRR) / 2 (0.5 = chance). On seed 927 plain accuracy chose "reject
everyone" (5 I × 1 L) and "accept everyone" (1 I × 5 L) at 0.83.

## Algorithm

```
draw users and session orders from seed (same draw as 08 / 10)
for each legitimate user u: library_k(u) = first k of u's sessions, k = 1 … m
test sessions: legitimate u → last m of u's sessions (never in a library), against u's own library
               impostor v   → first m of v's sessions, against each legitimate library, one attempt per library
for each test session and library session (DTW once, cached in cache/distances.pkl):
    d[chunk] = min over library chunks of the same kind of banded DTW cost / resample_n
best distance with k sessions = running minimum of d over library sessions 1 … k
session accepted at (k, s)  ⇔  share of chunks with distance ≤ s  ≥  match_shape_ratio
user through                ⇔  share of the user's test sessions accepted  ≥  match_session_ratio
```

Why distances instead of rerunning 04 for every value: the DTW pass runs once per pair of sessions, and each of the
100 sensitivities is then only a comparison, so all 16,000 matrices cost seconds after it. At a given sensitivity
the match counts equal `04.matched_chunks` exactly (checked on a sample session). The test sets stay fixed while the
library grows, so session counts are compared on the same sessions.
