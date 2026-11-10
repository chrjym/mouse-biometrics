# Presentation Script: Feature Extraction — Results and Discussion

Run 19399f · seed 945 · split 5L × 1I · EARL sensitivity 0.02 · 0.5 s strokes · concave ratio 0.15

Total time: about 12–15 minutes. Say the **"Say"** parts aloud. Point at the numbers in **bold**.

---

## Slide 1 — Overview of the process (≈ 1 min)

**Show:** the flow.

```
Sessions → Screen (EARL DTW) → 0.5 s stroke → Align (0,0) → Convex hull
        → Concave hull → 64 data points → Euclidean distance → Accept / Reject
```

**Say:**
> "This part presents the results of feature extraction. From each session, one short mouse stroke of 0.5 seconds was taken. The strokes were aligned at a common starting point, wrapped with a convex hull, tightened into a concave hull, and resampled into 64 data points. These points were then compared using Euclidean distance to decide whether to accept or reject a user."

---

## Slide 2 — Stroke extraction and alignment (≈ 1 min)

**Show:** `user23_vs_user29_steps.png`, column 1.

**Say:**
> "The first stroke of each session lasting at least 0.5 seconds was cut to exactly 0.5 seconds. Every stroke was shifted so that it starts at the origin (0,0), so we compare the shape of the movement, not its position on the screen."

**Formula:** $\Delta x = x - x_0,\ \Delta y = y - y_0$

---

## Slide 3 — Convex hull (≈ 1 min)

**Show:** steps figure, column 2, and the table.

| | user23 | user29 |
|---|---|---|
| Corners | 9 | 11 |
| Convex area (px²) | 564,836 | 782,606 |

**Say:**
> "Using the Graham scan, the outermost points of all strokes were connected to form the convex hull, the smallest outline that encloses every stroke. user29 covers a larger area because its strokes reach far upward."

---

## Slide 4 — Concave hull (≈ 1.5 min)

**Show:** steps figure, column 3, and the table.

| | user23 | user29 |
|---|---|---|
| Edge limit L (px) | 116.6 | 149.6 |
| Corners | 42 | 52 |
| Concave area (px²) | 217,090 | 301,594 |
| % of convex | 38.4% | 38.5% |

**Formula:** $L = l_{min} + 0.15\,(l_{max} - l_{min})$

**Say:**
> "The convex hull includes a lot of empty space. Using Delaunay triangulation, long edges longer than the limit L were removed, so the outline follows the actual strokes. The concave hull keeps only about 38% of the convex area, giving a tighter and more personal shape."

---

## Slide 4b — Hull results of all users (Table 4) (≈ 1 min)

| User | Strokes tested (passed) | Convex area (px²) | Concave corners | Concave area (px²) | Concave / convex |
|---|---|---|---|---|---|
| user9 | 25 (23) | 584,226 | 50 | 236,902 | 40.5% |
| user15 | 25 (9) | 1,648,464 | 36 | 583,712 | 35.4% |
| user16 | 25 (12) | 695,418 | 52 | 196,514 | 28.3% |
| user20 | 25 (23) | 703,078 | 75 | 259,444 | 36.9% |
| user23 | 25 (11) | 564,836 | 42 | 217,090 | 38.4% |
| user29 | 25 (18) | 782,606 | 52 | 301,594 | 38.5% |
| user35 | 1 (0) | 305 | 5 | 226 | 74.1% |
| user7 | 1 (0) | 13,642 | 26 | 3,680 | 27.0% |

**Table 4.** Convex and concave hulls of each user's mixed hull (all tested 0.5 s strokes; passed in parentheses).

**Say:**
> "Table 4 shows the hull results for all users. Each user has a different hull size and number of corners, and the concave hull keeps only about 27–41% of the convex area. user15 has the largest area, 1.6 million px², because its strokes vary widely — only 9 of 25 sessions passed. user35 and user7 had only one tested stroke each, so their hulls are very small."

---

## Slide 5 — Data points and feature vector (≈ 1.5 min)

**Show:** steps figure, column 4.

| | user23 | user29 |
|---|---|---|
| Perimeter (px) | 4,621 | 4,846 |
| Spacing = P ÷ 64 (px) | 72.2 | 75.7 |
| Point 0 | (9, 361) | (410, 444) |

**Formula:** $s_i = \frac{i}{64}P$, $\quad H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$

**Say:**
> "Each concave hull has a different number of corners — 42 versus 52 — so they cannot be compared directly. Each outline was therefore resampled into 64 equally spaced points, starting from the lowest corner and moving counter-clockwise. This gives every user the same 128-value feature vector."

---

## Slide 6 — Euclidean distance: user23 vs user29 (≈ 2 min)

**Show:** `user23_vs_user29.png` (profiles).

| Result | Value |
|---|---|
| Total Euclidean distance | **3,353 px** |
| RMS gap per point | **419.1 px** |
| Smallest gaps | point 13 (136.4 px), point 27 (142.4 px) |
| Largest gap | **point 33 (671.4 px)** |

**Formula:** $d = \sqrt{\sum g_i^2}$, $\quad d_{RMS} = d / 8$

**Say:**
> "Comparing the 64 points of user23 and user29, the total distance was 3,353 pixels, or about 419 pixels per point. The gap is not equal everywhere. It is smallest at points 13 and 27, where both users move sideways in a similar way, and largest at point 33 — the tip of user29's upward movement, where user23 has no strokes. So the distance shows exactly where two users' habits differ: here, in vertical movement."

---

## Slide 7 — Test hull vs profile (Table 5) (≈ 1.5 min)

**Show:** `user23_user29_table5.png` and the table.

**Table 5.** RMS distance (px) of every test hull (row) to every profile (column); bold = own profile.

| Test hull ↓ / Profile → | user15 | user16 | user20 | user23 | user29 | user9 |
|---|---|---|---|---|---|---|
| user15 | **462.4** | 818.8 | 539.5 | 591.0 | 854.5 | 650.8 |
| user16 | 466.9 | 612.6 | 532.9 | 514.6 | 637.1 | 693.2 |
| user20 | 624.8 | 463.6 | **2.2** | 257.5 | 484.5 | 353.6 |
| user23 | 720.8 | 422.3 | 283.7 | **122.1** | 418.0 | 345.1 |
| user29 | 872.3 | 291.4 | 484.3 | 418.1 | **7.6** | 538.8 |
| user35 | 627.7 | 312.0 | 450.7 | 431.0 | 446.1 | 503.7 |
| user7 | 760.4 | 275.9 | 546.1 | 481.0 | 372.7 | 620.4 |
| user9 | 796.7 | 394.0 | 384.3 | 420.1 | 523.7 | **91.1** |

Focus on user23 and user29:

| Test hull → profile | RMS distance (px) | Meaning |
|---|---|---|
| user23 → user23 | **122.1** | same user, close |
| user23 → user29 | 418.0 | different user, far |
| user29 → user29 | **7.6** | same user, almost identical |
| user29 → user23 | 418.1 | different user, far |

**Say:**
> "Here, each user's test strokes were compared with the enrolled profiles. user29 is only 7.6 pixels from its own profile, and user23 is 122.1 pixels from its own — but both are about 418 pixels from each other. Looking at the whole table, every legitimate user's smallest value is on their own profile (in bold), so each user is closest to their own profile."

---

## Slide 8 — Performance evaluation: setup (≈ 1 min)

- Goal: can 0.5 s concave-hull outlines authenticate users?
- Score: Euclidean distance (RMS px per point)
- Rule: Distance ≤ T → **Accept**; Distance > T → **Reject**
- Trials: 8 test hulls × 5 legitimate profiles = **40** (5 genuine, 35 impostor)
- Metrics: identification accuracy, FAR, FRR, EER

**Say:**
> "To evaluate performance, all 8 test hulls were compared with the 5 legitimate profiles, giving 40 trials: 5 genuine and 35 impostor. user16's profile was excluded because it was built from wrongly accepted impostor sessions."

---

## Slide 8b — Identification result (≈ 1 min)

| User | Role | Nearest profile | Distance (px) | Result |
|---|---|---|---|---|
| user15 | legitimate | user15 | 462.4 | correct |
| user20 | legitimate | user20 | 2.2 | correct |
| user23 | legitimate | user23 | 122.1 | correct |
| user29 | legitimate | user29 | 7.6 | correct |
| user9 | legitimate | user9 | 91.1 | correct |
| user16 | impostor | user15 | 466.9 | rejected |
| user35 | impostor | user23 | 431.0 | rejected |
| user7 | impostor | user29 | 372.7 | rejected |

**Identification accuracy = 5/5 (100%).**

**Say:**
> "In identification, each test hull is assigned to its nearest profile. All five legitimate users were nearest to their own profile, giving 100% identification accuracy. The three impostors were nearest to other users' profiles, so none was identified as itself."

---

## Slide 9 — How the threshold was determined (≈ 1.5 min)

**Formulas:** $FAR = \frac{\text{impostors accepted}}{35}$, $\quad FRR = \frac{\text{genuine rejected}}{5}$, $\quad EER: FAR = FRR$

| T (px) | FAR | FRR | Accuracy |
|---|---|---|---|
| **122.1** | **0%** | 20% | **97.5%** (zero-FAR) |
| 257.5 | 2.9% | 20% | 95.0% |
| 384.3 | 17.1% | 20% | 82.5% |
| **418.0** | **20%** | **20%** | **80.0%** (EER) |
| 462.4 | 34.3% | 0% | 87.5% |

**Say:**
> "The threshold was not guessed. All 40 distances were sorted, and each one was tried as T. At each value, we counted impostors wrongly accepted and genuine users wrongly rejected. Two thresholds matter: 122.1 pixels, where no impostor gets in, and 418.0 pixels, where FAR equals FRR — the Equal Error Rate."

---

## Slide 10 — Genuine users (≈ 1 min)

| User | Distance (px) | Sessions passed | T = 122.1 | T = 418.0 |
|---|---|---|---|---|
| user20 | 2.2 | 23/25 | Accepted | Accepted |
| user29 | 7.6 | 18/25 | Accepted | Accepted |
| user9 | 91.1 | 23/25 | Accepted | Accepted |
| user23 | 122.1 | 11/25 | Accepted | Accepted |
| user15 | 462.4 | 9/25 | **Rejected** | **Rejected** |

**Say:**
> "Four of the five genuine users were accepted at both thresholds. user20 and user29 matched almost perfectly. Only user15 was rejected, because only 9 of its 25 sessions passed screening, so its profile was inconsistent. FRR is therefore 20%."

---

## Slide 11 — Impostors accepted at T = 418.0 px (≈ 1 min)

| Impostor → claimed profile | Distance (px) |
|---|---|
| user20 → user23 | 257.5 (lowest) |
| user23 → user20 | 283.7 |
| user23 → user9 | 345.1 |
| user20 → user9 | 353.6 |
| user7 → user29 | 372.7 |
| user9 → user20 | 384.3 |
| user23 → user29 | 418.0 |
| **FAR** | **7/35 = 20%** |

**Say:**
> "At 418 pixels, seven of the 35 impostor attempts were wrongly accepted. Most involve user9, user20 and user23, whose strokes overlap sideways. The other 28 attempts — 80% — were rejected."

---

## Slide 12 — Final result (≈ 1 min)

| Measure | Result |
|---|---|
| Identification accuracy | **100%** (5/5) |
| Zero-FAR (T = 122.1 px) | FAR 0%, FRR 20%, accuracy **97.5%** |
| EER (T = 418.0 px) | **EER = 20%**, accuracy 80% |

**Say:**
> "In summary: all five legitimate users were identified correctly. At the strict threshold, every impostor was blocked with 97.5% accuracy. At the balanced threshold, the Equal Error Rate was 20%."

---

## Slide 13 — Discussion and limitations (≈ 1 min)

- Geometry carries identity: user29 moves upward, user23 sideways.
- Consistent enrollment means a better match (user20: 23/25 → 2.2 px; user15: 9/25 → 462.4 px).
- Similar sideways movers (user9, user20, user23) cause most false accepts.
- Limitation: only 5 genuine trials, so one error changes FRR by 20 points.

**Say:**
> "The results show that the shape of a short movement reflects a user's habit. Users with consistent sessions matched best. The main weakness is users with few passed sessions, and the small number of trials, so more users and sessions are needed."

---

## Slide 14 — Conclusion (≈ 30 s)

> **"A single 0.5-second mouse stroke, turned into a concave-hull outline of 64 points, can distinguish users: 100% identification, 0% FAR at T = 122.1 px, and an EER of 20%."**

---

## Possible questions and answers

| Question | Answer |
|---|---|
| Why 64 points? | Hulls have different numbers of corners (42 vs 52); 64 equal points give every user the same 128-value vector so they can be compared point by point. |
| Why concave instead of convex? | The convex hull includes empty space; the concave hull keeps about 38% of it and follows the real strokes, so it is more personal. |
| Why ratio 0.15? | It removes long empty edges while keeping the outline closed; it was the setting fixed for this run. |
| Why divide by 8? | $\sqrt{64} = 8$; it turns the total distance into the average gap per point (RMS), which is easier to read in pixels. |
| Why is user16 excluded? | Its profile was built from wrongly accepted impostor sessions, so it is not a valid legitimate template. |
| Why did user15 fail? | Only 9/25 sessions passed screening, so its profile does not represent its normal movement (self-distance 462.4 px). |
| Why is the figure 419.1 px but Table 5 says 418.0? | The figure compares the two **profiles**; Table 5 compares a **test hull** with a **profile**. |
| Is 20% EER good? | It is a starting result from one 0.5 s stroke and only 5 genuine trials; the zero-FAR setting already blocks all impostors. More data is needed. |
| Was the held-out test run? | No; this evaluation uses the 19399f run only. |
