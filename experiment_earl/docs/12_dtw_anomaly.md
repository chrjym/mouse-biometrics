# `12_dtw_anomaly.py`: anomaly test with DTW shape matching

[← index](README.md) · previous: [11](11_ocsvm_anomaly.md) · next: [13](13_enroll_sweep.md)

## What it does

Same protocol, window rule and EER as [10](10_hull_anomaly.md), but the question per stroke is the
shape-matching question of [04](04_match_shapes.md): **does the user's library contain a stroke of the same
shape?** A stroke with no match is "outside". This puts the DTW shape matching on the same scale as the hull and
the SVM, so the three can be compared by EER.

Outputs: `runs/<run>/results/dtw/{sessions,summary}.csv`, `results/dtw/progress.pkl`, `figures/dtw_anomaly.png`.

## Algorithm

### 1. Shapes of a session (`session_shapes`)

Every stroke from `segment` (03) is normalized (start at the origin, bounding-box diagonal 1, 64 points evenly
spaced by arc length) and labelled move or drag. Strokes too flat to normalize are left out.

### 2. Library (`build_library`)

```
paths, kinds ← all shapes of the k enrolled sessions
if more than dtw_max_library: keep a random subset of dtw_max_library (seeded)
library      ← {move: move shapes, drag: drag shapes}
```

**Why cap at 4000?** Each test stroke is compared, in the worst case, with every library shape, so the time
grows with the library size. 4000 is the same cap as the SVM's training set, so every method sees as much of the
user's data. Removing the cap for user12 (4000 → ~5100 shapes) changed their EER only from 59.9% to 57.9%, so the
cap does not hide much.

### 3. Anomalous strokes (`anomalous`)

$$o_i = \begin{cases} 0 & \exists\, b \in \text{library}_{\text{kind}(i)} : \ \text{DTW}(a_i, b)/n \le \texttt{dtw\_tolerance} \\ 1 & \text{otherwise}\end{cases}$$

The test is `has_match` from 04: banded DTW (band $w = \operatorname{round}(0.1 \cdot 64) = 6$), early
abandoning, stop at the first match. See [04](04_match_shapes.md) for the recurrence and why we use DTW.

### 4. Windows and session score (`score`)

Exactly as in 10:

$$w_j = \frac{1}{W}\sum_{i=j}^{j+W-1} o_i, \qquad \text{flag window if } w_j > \texttt{anomaly\_outside\_share}, \qquad s = \max_j w_j$$

The EER function is the hull's (a high score means anomalous).

### 5. Resume

Each finished user is saved to `progress.pkl`, and a rerun skips them. It takes about one minute per user.

## Why test DTW this way

Scripts 04–06 ask "does an **impostor user** match a profile?", a yes/no decision per user. Here the same matching
gives a per-session score, an FRR and a FAR on the **same sessions and enrollments** as the hull and the SVM. This
is the fair comparison: same data, same window rule, same EER, only the stroke test differs.

## Settings used

`dtw_tolerance`, `dtw_band`, `resample_n`, `dtw_max_library`, plus `anomaly_enroll_sessions`, `anomaly_window`,
`anomaly_outside_share` from 10.

## What we learned (tolerance 0.02, library 4000)

- **EER 43.7%**, the same as the hull (43.8%) and worse than the One-Class SVM (29.6%).
- About 75% of **every** stroke has no match, whether own or impostor (74.1% vs 77.7%). At the fixed 20% rule
  every session is therefore flagged (FRR 100%, FAR 0%). This is why methods must be compared by EER, not by FRR
  and FAR at a fixed rule.
- Results are uneven per user: user9 0%, user20 17.5%, user16 73%.
