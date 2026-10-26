# Sensitivity Sweep: How Well Stroke Shape Separates Users

One full grid: every sensitivity × every library size × every user mix, with one confusion matrix per setting.
No single best setting is picked; the whole grid is the result.

> **In simple terms:** instead of tuning a radio to one "best" station, we record how clear the signal is at
> every dial position and antenna length, then look at the whole map. If the map is flat at 0.5, there is no
> station to find.

Code: [`src/13_sweep_sensitivity.py`](src/13_sweep_sensitivity.py) (counts) and
[`src/14_plot_sweep.py`](src/14_plot_sweep.py) (figures). Settings: the sweep keys of [`config.yaml`](config.yaml).

---

## 1. The question

**Across different impostor/legitimate mixes, at which sensitivity and library size (if any) does stroke shape
separate impostors from legitimate users better than chance?**

## 2. The parts

| Part | Values | Meaning |
|---|---|---|
| **Data** | Balabit, 10 users | Sessions labelled `is_illegal = 1` are dropped (`labels_file`) |
| **Seed** | 945 | Picks the users of each mix and shuffles each user's sessions once |
| **Mixes (L × I)** | 1 × 5, 5 × 1, 3 × 2, 2 × 3 (`splits`) | Legitimate users × impostor users; each mix is its own draw from the seed |
| **Sensitivity** | 0.01 → 1.00, step 0.01 (`sweep_sensitivity`, 100 values) | How lenient a stroke match is; higher = more lenient |
| **Library size** | 1 → 40 (`sweep_sessions_max`) | A legitimate user's first k sessions form their profile; library k + 1 = library k plus one session |
| **Test sessions** | 40 per user (`sweep_test_sessions`) | Never part of any library; the same sessions at every library size |

A user's session order is the same at every library size, so a bigger library only adds sessions.

## 3. How one attempt is decided

1. **Legitimate user:** each of their last 40 sessions is tested against their **own** library.
2. **Impostor:** each of their first 40 sessions is tested against **each** legitimate library, as a separate
   attempt (40 × L attempts per impostor). An impostor is not let in just because one of several libraries passes.
3. **Stroke match:** a stroke matches when its DTW distance to the closest library stroke of the same kind is
   ≤ the sensitivity.
4. **Session accepted:** when ≥ `match_shape_ratio` (20%) of its strokes match.

DTW runs once per (test session, library session). A library of k sessions takes the smallest distance over its
k sessions, and each sensitivity is only a cut on those saved distances.

## 4. The confusion matrix

Positive = impostor; rows = decision, columns = truth.

|  | **Actual Impostor** | **Actual Legitimate** |
|---|---|---|
| **Rejected (predicted impostor)** | **TP**: impostor caught ✅ | **FP**: real user blocked ❌ |
| **Accepted (predicted legitimate)** | **FN**: impostor let in ❌ | **TN**: real user accepted ✅ |

### Counted fresh, never appended

```
for each mix:
    for each library size k = 1 … 40:
        for each sensitivity s = 0.01 … 1.00:
            TP = FP = FN = TN = 0                      ← starts at zero
            each legitimate test session: accepted → TN, rejected → FP
            each impostor (session, library) attempt: accepted → FN, rejected → TP
            save one row
```

- Inside one matrix, every attempt adds 1 to exactly one box.
- Between library sizes, sensitivities and mixes nothing carries over: each is its own matrix.
- 4 mixes × 40 library sizes × 100 sensitivities = **16,000 matrices**.

Example, mix 3 L × 2 I: legitimate 3 × 40 = 120 sessions (TN + FP); impostor 2 × 40 × 3 = 240 attempts
(TP + FN); 360 attempts in every matrix of that mix.

### User level

Each matrix is also counted per user (`users_TP`, `users_FP`, `users_FN`, `users_TN`): a user counts as accepted
when ≥ `match_session_ratio` of their attempts pass.

## 5. The scores

| Score | Formula | Meaning |
|---|---|---|
| **Accuracy** | (TP + TN) / all attempts | Share of right decisions; misleading when the mix is lopsided |
| **FAR** | FN / impostor attempts | Impostors let in (security error) |
| **FRR** | FP / legitimate sessions | Real users blocked (convenience error) |
| **Balanced accuracy** | 1 − (FAR + FRR) / 2 | Weighs both sides equally; the main score |

**0.5 = chance:** accepting everyone (FAR 1, FRR 0) or rejecting everyone (FAR 0, FRR 1) both give 0.5.
1.0 = perfect; below 0.5 = worse than guessing.

## 6. The whole flow

```
 seed 945 → draw users per mix (1×5, 5×1, 3×2, 2×3), drop illegal sessions
   │
   ▼
 libraries: each legitimate user's first 1 … 40 sessions
   │
   ▼
 test: legitimate last 40 vs own library
       impostor first 40 vs each legitimate library (separate attempts)
   │
   ▼
 DTW once per session pair → cut at every sensitivity
   │
   ▼
 one fresh TP / FP / FN / TN per (mix, library size, sensitivity) → confusion.csv
   │
   ▼
 figures: accuracy vs sensitivity, heatmap, FAR / FRR
```

## 7. The figures (14)

| Figure | x | y | Shows |
|---|---|---|---|
| `accuracy_vs_sensitivity.png` | Sensitivity | Balanced accuracy | One panel per mix, lines at 1, 10, 20, 40 sessions; dashed line = 0.5 |
| `accuracy_heatmap.png` | Sensitivity | Library size | Colour = balanced accuracy: blue = better than chance, white = 0.5, red = worse |
| `far_frr.png` | Sensitivity | FAR, FRR | Where letting impostors in trades against blocking real users |
| `confusion_matrices.png` | Actual class | Decision | 2 × 2 matrices per mix at sensitivity 0.01, 0.02, 0.05, 0.10 (40 sessions): counts and share of each column |

## 8. Why no best setting is picked

Each mix has 4,000 cells scored on the same data. Even with no real signal, the highest of 4,000 noisy cells sits
above 0.5, so a "best" would overstate the method. The grid is read as a whole instead.

## 9. Reading the result

- **A region clearly above 0.5** (blue in the heatmap, in every mix): stroke shape carries some identity there.
- **The region moves with the mix:** the result depends on how common impostors are, which is itself a finding.
- **Everything near 0.5:** the method cannot separate users at any sensitivity or library size.
- **Below 0.5** (red, e.g. 1-session libraries): real users are blocked more often than impostors.

Outputs: `runs/<hash>/sweep/` (`confusion.csv`, `parts/`, `config.yaml`, the four figures).
