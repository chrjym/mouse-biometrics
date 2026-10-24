# Sensitivity Sweep: Process and Results

Oct 23, 2026 · @Thesis Agent

## Summary

No sensitivity setting lets real users in while keeping impostors out: the best balanced accuracy is 0.60, and 0.5 is guessing.

The sweep asked one question: which sensitivity, and how many past sessions per user, best separate legitimate users from impostors when users are recognised by the shape of their mouse strokes?

- **Best result:** 0.60, for 1 legitimate user vs 5 impostors at sensitivity 0.05 with a 2-session library. The other three splits reach only 0.50 to 0.55.
- **Where sensitivity matters:** only between 0.01 and about 0.05. From about 0.06 upward, every session is accepted and the score sits at chance, except with a 1-session library.
- **Why:** most mouse strokes are near-straight lines or plain curves, so one person's strokes look like anyone else's. Tuning the sensitivity cannot fix that.

The run covered 4 splits × 40 library sizes × 100 sensitivities = 16,000 settings, on seed 945.

## The setup

The sweep uses the Balabit mouse dataset (10 users, every session in each user's folder) and the settings below, fixed in `sweep.yaml` and `config.yaml`.

| Setting | Value | Meaning |
| --- | --- | --- |
| Seed | 945 | Fixes which users are drawn and the order of each user's sessions |
| Splits | 1 vs 5, 5 vs 1, 3 vs 2, 2 vs 3 | Legitimate users vs impostors in each test |
| Sensitivity | 0.01 to 1.00, step 0.01 (100 values) | Largest DTW distance per point that still counts as a match; higher = more lenient |
| Library size | 1 to 40 sessions | How many past sessions make up each legitimate user's profile |
| Test sessions | 40 per user | Legitimate: the user's last 40 sessions, never in the library. Impostor: their first 40 sessions |
| Stroke rule | 20% | A session is accepted when at least 20% of its strokes match the library |

Each split is its own random draw from the seed (`random.Random(945)`), so the users are not fixed: a different seed draws different legitimate and impostor users, and the same user can be legitimate in one split and an impostor in another. The draw for seed 945:

| Split | Legitimate | Impostors |
| --- | --- | --- |
| 1 legitimate vs 5 impostors | user29 | user9, user15, user20, user23, user35 |
| 5 legitimate vs 1 impostor | user9, user15, user20, user23, user29 | user16 |
| 3 legitimate vs 2 impostors | user20, user23, user29 | user9, user15 |
| 2 legitimate vs 3 impostors | user23, user29 | user7, user15, user20 |

## The process, step by step

Every setting goes through the same eight steps. DTW runs once per pair of sessions; each sensitivity is only a different cut on the saved distances.

1. **Cut sessions into strokes.** A new stroke starts after a pause longer than 0.5 s or at a click. Strokes with fewer than 10 points are dropped as jitter.
2. **Redraw each stroke.** Every stroke is resampled to 64 evenly spaced points and normalised, so strokes of any size compare as shapes.
3. **Build each library.** A legitimate user's library is their first k sessions, for k = 1 to 40.
4. **Pick the test sessions.** Legitimate: the user's last 40 sessions, never in a library. Impostor: their first 40 sessions, tested against every legitimate library.
5. **Compare strokes with DTW.** For each test stroke, banded dynamic time warping finds the closest library stroke. The band lets a shape stretch by at most 10%. The result is a distance per point: 0 = identical.
6. **Decide accept or reject.** A stroke matches when its distance is at most the sensitivity. A session is accepted when at least 20% of its strokes match. An impostor session counts as accepted when it passes any one of the legitimate libraries.
7. **Count outcomes.** Positive = impostor: TP = impostor rejected, FN = impostor accepted, TN = real user accepted, FP = real user rejected.
8. **Score each setting.**

&#91;embedded content: decision for one test session at one sensitivity and library size\]

The sweep repeats this decision for every test session at all 100 sensitivities and 40 library sizes, then counts the outcomes.

```latex
\mathrm{FAR} = \frac{FN}{\text{impostor sessions}} \qquad \mathrm{FRR} = \frac{FP}{\text{legitimate sessions}} \qquad \text{balanced accuracy} = 1 - \frac{\mathrm{FAR} + \mathrm{FRR}}{2}
```

Balanced accuracy is 0.5 for any setting that rejects everyone or accepts everyone, so 0.5 = chance in every split. Plain accuracy is not used to pick the best: in the 1 vs 5 split, rejecting everyone already scores 0.83.

## Results

Every best setting wins by giving up one side: it either blocks most real users or lets most impostors in.

| Split | Best sensitivity | Library (sessions) | Balanced accuracy | Impostors let in (FAR) | Real users blocked (FRR) | EER |
| --- | --- | --- | --- | --- | --- | --- |
| 1 legitimate vs 5 impostors | 0.05 | 2 | 0.603 | 17% | 63% | 0.443 |
| 5 legitimate vs 1 impostor | 0.02 | 9 | 0.552 | 3% | 87% | 0.480 |
| 3 legitimate vs 2 impostors | 0.02 | 5 | 0.506 | 4% | 95% | 0.560 |
| 2 legitimate vs 3 impostors | 0.04 | 10 | 0.504 | 92% | 8% | 0.529 |

- **1 vs 5:** the highest score, but it stops impostors by blocking 63% of user29's own sessions. Only 40 legitimate sessions are tested, so a few sessions move the score a lot.
- **5 vs 1 and 3 vs 2:** almost no impostor gets in, because 87% to 95% of real sessions are blocked too.
- **2 vs 3:** the opposite: real users get in, and so do 92% of impostor sessions.
- **EER** (where FAR equals FRR) is 0.44 to 0.56 in every split, which is chance level.

A working system would keep both FAR and FRR low at the same setting. No cell of the 16,000 does that.

### The confusion matrices behind the best settings

Each matrix counts every test session at that split's best setting; positive = impostor, so the top row is what the system rejected.

&#91;image: Confusion matrix at the best setting of each split\]

How to read one matrix:

|  | Actually impostor | Actually legitimate |
| --- | --- | --- |
| **Rejected** (predicted impostor) | **TP**: impostor caught | **FP**: real user blocked |
| **Accepted** (predicted legitimate) | **FN**: impostor let in | **TN**: real user let in |

TP and TN are correct decisions; FP and FN are the two errors. In the figure, the diagonal cells (TP, TN) are always the darker blue, whatever their count, so read the numbers, not the shade.

All four, with the rates worked out:

| Split | TP | FP | FN | TN | FAR = FN / impostor sessions | FRR = FP / legitimate sessions | Balanced accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 legitimate vs 5 impostors | 166 | 25 | 34 | 15 | 34 / 200 = 0.17 | 25 / 40 = 0.63 | 0.60 |
| 5 legitimate vs 1 impostor | 39 | 174 | 1 | 26 | 1 / 40 = 0.03 | 174 / 200 = 0.87 | 0.55 |
| 3 legitimate vs 2 impostors | 77 | 114 | 3 | 6 | 3 / 80 = 0.04 | 114 / 120 = 0.95 | 0.51 |
| 2 legitimate vs 3 impostors | 10 | 6 | 110 | 74 | 110 / 120 = 0.92 | 6 / 80 = 0.08 | 0.50 |

What each one says:

- **1 legitimate vs 5 impostors:** 166 of 200 impostor sessions are caught, but only 15 of user29's 40 own sessions get in. The system is safe because it is strict with everyone.
- **5 legitimate vs 1 impostor:** 39 of 40 impostor sessions are caught, but 174 of 200 real sessions are blocked. A guard who stops nearly everyone also stops the one impostor.
- **3 legitimate vs 2 impostors:** the same pattern, stronger: only 6 of 120 real sessions get in.
- **2 legitimate vs 3 impostors:** the reverse: 74 of 80 real sessions get in, but so do 110 of 120 impostor sessions.

In every matrix, one error column is large. A useful system would have small FP and small FN at the same setting; none of the four does. Plain accuracy hides this: the first matrix scores 0.75 plain accuracy only because 200 of its 240 test sessions are impostors.

## Reading the figures

All the action sits between sensitivity 0.01 and 0.08; past that, every split reads 0.50.

&#91;embedded content: confusion.csv, runs/526e7a/sweep · 10-session library, sensitivity 0.01 to 0.10\]

The same picture holds at every library size from 10 sessions up. The two figures the sweep writes show it for all sizes at once.

**`accuracy_vs_sensitivity.png`.** One panel per split; the x-axis is zoomed to where anything changes (about 0.01 to 0.47).

- **Dark blue lines (10, 20, 40 sessions):** a small wiggle at 0.01 to 0.05, then flat on the 0.5 chance line.
- **Light blue line (1 session):** drops to about 0.25 to 0.33 in three splits, then climbs back to 0.5 by about 0.45.
- **Grey band:** the lowest to highest score over all 40 library sizes.
- **Star:** each split's best setting, with its score.

&#91;image: Balanced accuracy against sensitivity, one panel per split, lines for 1, 10, 20 and 40 sessions\]

**`accuracy_heatmap.png`.** Each small square is one setting: sensitivity across, library size up.

- **Colour:** blue = better than guessing, white = guessing (0.5), red = worse than guessing.
- **Almost all white:** for nearly every setting the system only guesses.
- **Thin strip at the left (0.01 to 0.05):** the only place sensitivity matters. It is mostly red, and pale blue only in 1 legitimate vs 5 impostors.
- **Red bottom row:** with a 1-session library the system does worse than guessing up to about 0.35 to 0.45 in three splits.
- **Stars:** the best cells sit at low sensitivity and small libraries, barely darker than the white around them.

&#91;image: Heatmap of balanced accuracy, sessions by sensitivity, one panel per split\]

## Why it turns out this way

Three causes, each visible in the results:

1. **Strokes look alike across people.** Most strokes are near-straight lines or plain curves. After resampling and normalising, user A's straight line and user B's straight line are almost the same shape, so DTW distances for genuine and impostor pairs overlap.
2. **Small libraries are unfair to the real user.** One session does not cover a user's own range of strokes, so their new sessions match poorly, while impostors still find chance matches. That is the red bottom row of the heatmap.
3. **Impostors get several chances.** An impostor session is accepted when it matches any one of the legitimate libraries. With 2 to 5 libraries to try, impostors pass more easily than real users, which is why the splits with several legitimate users score below chance.

### Compared with earlier runs

| Run | Seed | Sensitivity grid | Best setting | Best score |
| --- | --- | --- | --- | --- |
| This sweep (coarse) | 945 | 0.01 to 1.00, step 0.01 | 0.02 to 0.05, 2 to 10 sessions | 0.50 to 0.60 balanced accuracy |
| Fine sweep, same day | 945 | 0.010 to 0.060, step 0.001 | 0.016 to 0.053; best on average 0.022 | 0.53 to 0.63 balanced accuracy |
| Initial report, 2026-10-19 | 927 | 0.01 to 0.50, step 0.01 | 0.03, 8 sessions | 0.52 to 0.71 user accuracy |

All three agree: the useful range is about 0.02 to 0.04, and stroke shape gives only weak separation. The initial report scores whole users (a user passes when half their sessions pass), so its numbers run higher and are not directly comparable. A coarse rerun on seed 945 reproduced this sweep's numbers exactly.

### Limits

- **Chosen on the same data:** each best setting is picked and scored on the same draw, so the scores are upper bounds.
- **One draw:** a single seed fixes which users are legitimate or impostors. The 2026-10-19 seed check found that settings chosen on seed 927 fell to chance on seeds 928 to 930.
- **Small samples:** the 1 vs 5 split tests only 40 legitimate sessions.

## Conclusion and next steps

Using only stroke shape compared with DTW, the system cannot reliably tell real users from impostors, whatever the sensitivity or library size.

A sentence for the thesis: *"Stroke shape compared with banded DTW reached at most 0.60 balanced accuracy (chance = 0.5) across 16,000 settings of sensitivity, library size and user mix, because most mouse strokes are simple lines and curves shared by all users."*

What the sweep still settles:

- **Sensitivity range:** 0.01 to 0.05 is the only range worth searching; values above it accept everyone.
- **Library size:** 1-session libraries do worse than chance and should not be used.
- **Decision rule:** accepting an impostor who matches any library favours impostors; testing against the claimed user's library only would be fairer.
- **Features:** the next step from the 2026-10-19 report is to add how a stroke is drawn (speed, acceleration, pauses), not only its shape.

### How to reproduce

Run from the repo root. The run takes about 1.5 minutes with a warm DTW cache.

```
.venv/bin/python experiment_earl/src/16_sweep_sensitivity.py
.venv/bin/python experiment_earl/src/17_plot_sweep.py
```

Outputs land in `experiment_earl/runs/526e7a/sweep/`: `confusion.csv` (16,000 rows), `best.csv`, `accuracy_vs_sensitivity.png`, `accuracy_heatmap.png`, `far_frr.png`, `confusion_best.png`. The output folder does not depend on the sensitivity grid, so move or delete an old `sweep/` folder before running a new grid.
