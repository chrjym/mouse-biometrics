# Feature Extraction: user23 vs user29

Run `19399f` (seed 945), split 5L × 1I, sensitivity 0.02, 25 sessions. Values are from the **mixed hulls** (all 25 tested strokes of each user, legitimate and impostor together; passed strokes in parentheses), 0.5 s strokes, concave ratio 0.15, 64 data points.

Source: `experiment_earl/runs/19399f/concave_hull_mixed_0.5s/<user>/` (`hull.csv`, `data_points.csv`, `stroke_points.csv`). Notebook: `experiment_earl/notebooks/passed_strokes.ipynb`, sections 7–9.

## Mixed hulls of all users (Table 4)

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

**Table 4.** Convex and concave hulls of each user's mixed hull (all tested 0.5 s strokes; passed strokes in parentheses).

Source: `experiment_earl/runs/19399f/concave_hull_mixed_0.5s/<user>/hull.csv`.

## Methods used

| Stage | Method | Tool / source | Setting |
|---|---|---|---|
| Data | Balabit Mouse Dynamics Challenge dataset; sessions with `is_illegal = 1` removed | `datasets/balabit/users/` | 10 users; seed 945 draws the users and session order |
| Session screening | EARL shape matching: banded Dynamic Time Warping (DTW) between a session's strokes and the legitimate user's library | `earl_simulation.ipynb` → `runs/19399f/best/best_sessions.csv` | sensitivity 0.02, DTW band 0.1, session passes at ≥ 20% matched strokes, 25 sessions |
| Stroke segmentation | Pause-based segmentation; first stroke lasting ≥ 0.5 s, cut to exactly 0.5 s | `passed_strokes.ipynb` sections 3–4 | pause > 0.5 s or a click ends a stroke |
| Grouping | Profile = passed strokes; mixed hull = all tested strokes | sections 3–4 | this file uses the **mixed hull** |
| Alignment | Translation to the origin | section 3 | $\Delta x = x - x_0,\ \Delta y = y - y_0$ |
| Convex hull | Graham scan | section 6 | cross product $(x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$ |
| Area | Shoelace formula | sections 6, 8 | $\frac{1}{2}\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\rvert$ |
| Concave hull | Delaunay triangulation with edge erosion (Davis) | section 8 (`scipy.spatial.Delaunay`) | ratio 0.15; $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| Data points | Fixed start (lowest corner, counter-clockwise) and arc-length resampling | section 9 | 64 points; $s_i = \frac{i}{64}P$ |
| Feature vector | Stacking point coordinates | section 9 | $H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$, 128 values |
| Comparison | Euclidean distance between the two mixed hulls, reported as RMS gap per point | computed from section 9's `data_points.csv` | $d = \sqrt{\sum g_i^2}$, $d_{RMS} = d / \sqrt{64}$ |
| Decision | Nearest profile (identification); threshold T (verification); FAR, FRR, EER, accuracy | section 10, Chapter 3 | EER 20% at T ≈ 418 px |

## Formulas used

**1. Alignment**

$$\Delta x_t = x_t - x_0, \qquad \Delta y_t = y_t - y_0$$

**2. Convex hull (Graham scan)**

$$\mathrm{cross}(O,A,B) = (x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$$

**3. Area (shoelace)**

$$Area = \frac{1}{2}\left|\sum_{k=1}^{n}(x_k y_{k+1} - x_{k+1} y_k)\right|$$

**4. Concave hull edge limit (Delaunay erosion)**

$$L = l_{min} + r(l_{max} - l_{min}), \qquad r = 0.15$$

**5. Concave / convex ratio**

$$Ratio = \frac{Area_{concave}}{Area_{convex}} \times 100\%$$

**6. Perimeter**

$$P = \sum_{k=1}^{n}\sqrt{(x_{k+1} - x_k)^2 + (y_{k+1} - y_k)^2}$$

**7. Data point spacing and positions**

$$\Delta s = \frac{P}{64}, \qquad s_i = \frac{i}{64}P, \qquad i = 0, \dots, 63$$

**8. Feature vector**

$$H = (\Delta x_0, \Delta y_0, \Delta x_1, \Delta y_1, \dots, \Delta x_{63}, \Delta y_{63})$$

**9. Gap per point**

$$g_i = \sqrt{(\Delta x^A_i - \Delta x^B_i)^2 + (\Delta y^A_i - \Delta y^B_i)^2}$$

**10. Euclidean distance**

$$d(A,B) = \sqrt{\sum_{i=0}^{63} g_i^2}$$

**11. RMS gap per point**

$$d_{RMS} = \frac{d(A,B)}{\sqrt{64}}$$

**12. Evaluation**

$$FAR = \frac{\text{impostor attempts accepted}}{\text{all impostor attempts}}, \qquad FRR = \frac{\text{genuine attempts rejected}}{\text{all genuine attempts}}$$

$$Accuracy = \frac{\text{correct decisions}}{\text{all decisions}}, \qquad EER = FAR = FRR$$

## Compact table (for the paper)

| Steps | Value | user23 | user29 | Formula |
|---|---|---|---|---|
| Align (0,0) | Strokes tested (passed) | 25 (11) | 25 (18) | $\Delta x_t = x_t - x_0, \quad \Delta y_t = y_t - y_0$ |
| Convex hull | Corners / area (px²) | 9 / 564,836 | 11 / 782,606 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| Concave hull | Edge limit (px) / corners / area (px²) / share of convex | 116.6 / 42 / 217,090 / 38.4% | 149.6 / 52 / 301,594 / 38.5% | $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| Data points | Perimeter (px) / points / spacing (px) | 4,621 / 64 / 72.2 | 4,846 / 64 / 75.7 | $s_i = \frac{i}{64}P$ |
| Feature vector | Values | 128 | 128 | $H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$ |
| Euclidean distance | Total / RMS per point (px) | 3,337 / 417 | | $d = \sqrt{\sum g_i^2}, \quad d_{RMS} = \frac{d}{\sqrt{64}}$ |

## Summary

| Steps | Value | user23 | user29 | Formula |
|---|---|---|---|---|
| Sessions | Sessions passed / tested | 11 / 25 | 18 / 25 | — |
| Align (0,0) | Strokes tested (passed) | 25 (11) | 25 (18) | $\Delta x_t = x_t - x_0, \quad \Delta y_t = y_t - y_0$ |
| | Recorded points | 196 | 192 | — |
| | Horizontal reach Δx (px) | −871 to 787 | −308 to 871 | $\min \Delta x,\ \max \Delta x$ |
| | Vertical reach Δy (px) | −231 to 361 | −689 to 444 | $\min \Delta y,\ \max \Delta y$ |
| Convex hull | Corners | 9 | 11 | $\mathrm{cross}(O,A,B) = (x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$ |
| | Area (px²) | 564,836 | 782,606 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| Concave hull | Edge limit L (px) | 116.6 | 149.6 | $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| | Corners | 42 | 52 | edges $> L$ removed |
| | Area (px²) | 217,090 | 301,594 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| | Concave / convex | 38.4% | 38.5% | $\frac{Area_{concave}}{Area_{convex}} \times 100\%$ |
| Fixed start | Point 0 (Δx, Δy) | (9, 361) | (410, 444) | lowest corner, counter-clockwise |
| Data points | Perimeter P (px) | 4,621 | 4,846 | $P = \sum\sqrt{(x_{k+1} - x_k)^2 + (y_{k+1} - y_k)^2}$ |
| | Points | 64 | 64 | $s_i = \frac{i}{64}P, \quad i = 0, \dots, 63$ |
| | Spacing (px) | 72.2 | 75.7 | $\Delta s = \frac{P}{64}$ |
| Feature vector | Values | 128 | 128 | $H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$ |
| Euclidean distance | Gap per point | 409.5 (point 0) to 694.6 (point 33) | | $g_i = \sqrt{(\Delta x^A_i - \Delta x^B_i)^2 + (\Delta y^A_i - \Delta y^B_i)^2}$ |
| | Total distance (px) | 3,337 | | $d = \sqrt{\sum_{i=0}^{63} g_i^2}$ |
| | RMS gap per point (px) | 417 | | $d_{RMS} = \frac{d}{\sqrt{64}}$ |

Negative Δy is upward (screen coordinates).

## Computation

| Step | Value | How it is computed | user23 | user29 |
|---|---|---|---|---|
| **0. Sessions** | Passed / tested | A session passes when ≥ 20% of its strokes match the library (DTW, sensitivity 0.02) | 11 / 25 | 18 / 25 |
| **1. Align** | Strokes | One stroke per tested session: the first lasting ≥ 0.5 s, cut to 0.5 s | 25 | 25 |
| | Recorded points | All points of the strokes, pooled | 196 | 192 |
| | Aligned point | $\Delta x = x - x_0,\ \Delta y = y - y_0$ | each stroke's first point → (0, 0) | each stroke's first point → (0, 0) |
| | Reach | min and max of Δx, Δy | Δx −871 to 787; Δy −231 to 361 | Δx −308 to 871; Δy −689 to 444 |
| **2. Convex hull** | Corners | Graham scan: lowest point = anchor, sort by angle, keep left turns (cross > 0) | 9 | 11 |
| | Area | Shoelace: $\frac{1}{2}\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\rvert$ | 564,836 px² | 782,606 px² |
| **3. Concave hull** | Triangles | Delaunay triangulation of the distinct points | 169 points → 327 triangles, 495 edges | 166 points → 318 triangles, 483 edges |
| | Edge limit L | $L = l_{min} + 0.15(l_{max} - l_{min})$ | 1.0 + 0.15 × (771.7 − 1.0) = **116.6 px** | 1.0 + 0.15 × (991.7 − 1.0) = **149.6 px** |
| | Corners | Outer triangles with edges longer than L removed, longest first | 42 | 52 |
| | Area | Shoelace on the concave outline | 217,090 px² | 301,594 px² |
| | Share of convex | concave ÷ convex | 217,090 ÷ 564,836 = **38.4%** | 301,594 ÷ 782,606 = **38.5%** |
| **4. Fixed start** | Point 0 | Lowest corner (largest Δy), leftmost if tied; then counter-clockwise | (9, 361) | (410, 444) |
| **5. Data points** | Perimeter P | Sum of the outline's edge lengths | 4,621 px | 4,846 px |
| | Spacing | $P \div 64$ | 4,621 ÷ 64 = **72.2 px** | 4,846 ÷ 64 = **75.7 px** |
| | Point positions | $s_i = \frac{i}{64}P$, i = 0 … 63 | every 72.2 px along the outline | every 75.7 px along the outline |
| **6. Feature vector** | Length | 64 points × (Δx, Δy) | 64 × 2 = **128** | 64 × 2 = **128** |

### Step 7: Euclidean distance between the two vectors

| Value | How it is computed | Result |
|---|---|---|
| Gap at point 0 | $g_0 = \sqrt{(9 - 410)^2 + (361 - 444)^2} = \sqrt{160{,}801 + 6{,}889}$ | **409.5 px** |
| Gap at point 33 (largest) | user23 (−160.4, 11.3) vs user29 (1.7, −664.1): $\sqrt{162.1^2 + 675.4^2}$ | **694.6 px** |
| Sum of squared gaps | $\sum_{i=0}^{63} g_i^2$ | 11,135,764 px² |
| Total distance | $d = \sqrt{11{,}135{,}764}$ | **3,337 px** |
| RMS gap per point | $d \div \sqrt{64} = 3{,}337 \div 8$ | **417 px** |

## Notes

- All values match Table 4: user23 564,836 / 42 / 217,090 / 38.4%; user29 782,606 / 52 / 301,594 / 38.5%.
- $l_{min}$ = 1.0 px for both users because some recorded points are only 1 px apart, so the edge limit depends mostly on the longest edge (771.7 vs 991.7 px).
- Step 1 counts recorded points (196, 192); step 3 uses distinct points (169, 166), since every stroke starts at (0,0) and repeated points count once.
- At point 33, user29's outline is at the top of its upward arm (Δy −664) while user23's is near the middle (Δy 11.3), which gives the largest gap.
- The mixed hulls include impostor-tested strokes: 14 of user23's 25 and 7 of user29's 25 sessions did not pass.
- The mixed-to-mixed distance (3,337 px, 417 px per point) was computed from each mixed hull's `data_points.csv`; the notebook figures `user23_vs_user29.png` and `user23_vs_user29_steps.png` still show the profile comparison (3,353 px, 419 px).
- Steps 1–6 are feature extraction (Objective 3); step 7 is matching (Objective 4).
