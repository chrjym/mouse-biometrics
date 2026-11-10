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

## Point-by-point Euclidean distance: user23 vs user29

### Concept

Both concave hull outlines are converted into 64 points in the same order (from point 0, the lowest corner, counter-clockwise). Point *i* of user23 is compared with point *i* of user29, and the 64 gaps are combined into one distance.

- **Left panel (hull data points):** user23's outline (purple) and user29's outline (green), 64 points each; the ring marks point 0; each grey line joins point *i* of both users, and its length is the gap $g_i$. Short lines = the outlines are close; long lines = they differ.
- **Right panel (gap per point):** each bar is one grey line's length (points 0–63); the orange line is the RMS gap. Low bars = shared movement; tall bars = where the shapes differ.

$$g_i = \sqrt{(\Delta x^{23}_i - \Delta x^{29}_i)^2 + (\Delta y^{23}_i - \Delta y^{29}_i)^2}$$

$$d = \sqrt{\sum_{i=0}^{63} g_i^2} = \sqrt{11{,}135{,}764} = 3{,}337 \text{ px}, \qquad d_{RMS} = \frac{3{,}337}{\sqrt{64}} = 417.1 \text{ px per point}$$

### Table

| Item | user23 | user29 | Interpretation |
|---|---|---|---|
| Concave hull area (px²) | 217,090 | 301,594 | user29's hull is larger because its strokes reach far upward |
| Concave corners | 42 | 52 | user29's outline is more detailed |
| Movement reach | Δx −871 to 787 px (sideways) | Δy up to −689 px (upward) | user23 moves sideways; user29 also moves far upward |
| Data points | 64 | 64 | Both outlines resampled to the same number of points |
| Point 0 (Δx, Δy) | (9, 361) | (410, 444) | Gap at point 0 = 409.5 px |
| Total Euclidean distance | 3,337 px | | $d = \sqrt{\sum g_i^2}$ |
| Average gap per point (RMS) | 417.1 px | | $d_{RMS} = d / \sqrt{64}$ |
| Lowest gaps | 98.4 px (point 27), 111.8 px (point 13) | | Both outlines share similar sideways movement |
| Highest gaps | above 520 px (points 31–35) | | Upper part of the shape |
| Peak gap | 694.6 px (point 33) | | Tip of user29's upward arm, where user23 has no strokes |
| Distance to own profile | 122.1 px | 7.6 px | Each mixed hull is nearest to its own profile |
| Distance to the other's profile | 418.0 px (to user29) | 418.1 px (to user23) | About 418 px apart in both directions |
| Conclusion | The users differ mainly in vertical movement | | The concave hull distance shows where their habits differ |

### Explanation

To provide interpretable values of how the concave hull outline is compared point by point with the Euclidean distance, the researchers selected two subjects, user23 and user29, as an illustration. The concave hull of user29 covered 301,594 px² with 52 corners, while that of user23 covered 217,090 px² with 42 corners. user29's hull is larger mainly because its strokes reach far upward (to Δy = −689 px), while user23's strokes spread mostly sideways. Both outlines were resampled into 64 evenly spaced data points. Comparing the resampled points of both users, the total Euclidean distance was 3,337 px, an average of 417.1 px per point. The gap was not the same around the shape. It dropped to its lowest values at points 27 (98.4 px) and 13 (111.8 px), where both outlines share similar sideways movement. It peaked within the upper part of the shape (points 31 to 35, above 520 px), reaching 694.6 px at point 33, the tip of user29's upward arm, where user23 has no strokes. The Euclidean distance on the concave hull therefore shows where two users' movement habits differ, here mainly in vertical movement, and supports distinguishing between them.

## Point-by-point Euclidean distance: user23 vs user29 (profiles, matches the figure)

Figure: `experiment_earl/runs/19399f/hull_distance_0.5s/user23_vs_user29.png` (notebook section 10.1). Values are from the **profiles** (passed strokes only: 11 for user23, 18 for user29), so the hull values differ from Table 4 (mixed hulls).

### Hull values

| Steps | Value | user23 | user29 | Formula |
|---|---|---|---|---|
| Align (0,0) | Strokes (passed) | 11 | 18 | $\Delta x_t = x_t - x_0, \quad \Delta y_t = y_t - y_0$ |
| | Reach | Δx −634 to 787; Δy −231 to 361 | Δx −308 to 871; Δy −689 to 444 | $\min, \max$ of $\Delta x, \Delta y$ |
| Convex hull | Corners / area (px²) | 8 / 522,470 | 11 / 782,606 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| Concave hull | Edge limit (px) | 118.7 | 149.6 | $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| | Corners / area (px²) | 30 / 224,410 | 53 / 298,036 | edges $> L$ removed |
| | Share of convex | 43.0% | 38.1% | $\frac{Area_{concave}}{Area_{convex}} \times 100\%$ |
| Data points | Perimeter (px) / points / spacing (px) | 3,975 / 64 / 62.1 | 4,863 / 64 / 76.0 | $s_i = \frac{i}{64}P$ |
| | Point 0 (Δx, Δy) | (9, 361) | (410, 444) | lowest corner, counter-clockwise |

### Distance values

| Item | Value | Calculation | Interpretation |
|---|---|---|---|
| Gap at point 0 | 409.5 px | $\sqrt{(9 - 410)^2 + (361 - 444)^2}$ | Starting points of both outlines |
| Lowest gaps | 136.4 px (point 13), 142.4 px (point 27) | $g_i$ | Both outlines share similar sideways movement |
| Upper part of the shape | points 30–36 | $g_i$ | Rising gaps along user29's upward arm |
| Peak gap | 671.4 px (point 33) | user23 (−108.1, 6.6) vs user29 (−2.5, −656.4): $\sqrt{105.6^2 + 663.0^2}$ | Tip of user29's upward arm, where user23 has no strokes |
| Sum of squared gaps | 11,241,785 px² | $\sum_{i=0}^{63} g_i^2$ | — |
| Total Euclidean distance | 3,353 px | $d = \sqrt{11{,}241{,}785}$ | — |
| Average gap per point (RMS) | 419.1 px | $d_{RMS} = 3{,}353 \div \sqrt{64}$ | Orange line in the figure |

### How to read the figure

| Part | What it shows |
|---|---|
| Left panel | user23's (purple) and user29's (green) outlines, 64 points each; the ring marks point 0; each grey line joins the same point number on both outlines, and its length is the gap |
| Right panel | One bar per gap (points 0–63); low bars at points 13 and 27 = shared sideways movement; tall bars at points 30–36 = user29's upward arm |
| Orange line | RMS gap = 419 px per point |

### Explanation

To provide interpretable values of how the concave hull outline is compared point by point with the Euclidean distance, the researchers selected two subjects, user23 and user29, as an illustration. Built from their passed strokes (11 and 18), the concave hull of user29 covered 298,036 px² with 53 corners, while that of user23 covered 224,410 px² with 30 corners. user29's hull is larger mainly because its strokes reach far upward, while user23's strokes spread mostly sideways. Both outlines were resampled into 64 evenly spaced data points. Comparing the resampled points of both users, the total Euclidean distance was 3,353 px, an average of 419.1 px per point. The gap was not the same around the shape. It dropped to its lowest values at points 13 (136.4 px) and 27 (142.4 px), where both outlines share similar sideways movement. It rose within the upper part of the shape (points 30 to 36) and peaked at 671.4 px at point 33, the tip of user29's upward arm, where user23 has no strokes. The Euclidean distance on the concave hull therefore shows where two users' movement habits differ, here mainly in vertical movement, and supports distinguishing between them.

## Mixed hull vs profile distances (Table 5)

Source: `experiment_earl/runs/19399f/hull_distance_0.5s/mixed_vs_profiles.csv` and `identify.csv` (notebook section 10).

### How the table was produced

| Step | What was done | Formula | Output |
|---|---|---|---|
| 1. Two hulls per user | One 0.5 s stroke per session, aligned at (0,0); **profile** = passed strokes only, **mixed hull** = all tested strokes | $\Delta x_t = x_t - x_0, \quad \Delta y_t = y_t - y_0$ | 6 profiles (user9, user15, user16, user20, user23, user29); 8 mixed hulls (user35 and user7 have no profile) |
| 2. Concave hull | Convex hull (Graham scan), refined by Delaunay erosion | $L = l_{min} + 0.15(l_{max} - l_{min})$ | `concave_hull_0.5s/<user>/`, `concave_hull_mixed_0.5s/<user>/` |
| 3. Feature vector | Outline resampled to 64 points from the lowest corner, counter-clockwise | $s_i = \frac{i}{64}P, \quad H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$ | `data_points.csv`, 128 values per hull |
| 4. Compare | Every mixed hull (rows) against every profile (columns): 8 × 6 = 48 comparisons | $g_i = \sqrt{(\Delta x^{mixed}_i - \Delta x^{profile}_i)^2 + (\Delta y^{mixed}_i - \Delta y^{profile}_i)^2}$ | — |
| 5. Distance | Gaps combined into one value per pair, rounded to 1 decimal | $d = \sqrt{\sum_{i=0}^{63} g_i^2}, \quad d_{RMS} = \frac{d}{\sqrt{64}}$ | `mixed_vs_profiles.csv` |
| 6. Identify | Smallest value in each row = nearest profile; verified when it is the user's own | $\min_{profile} d_{RMS}$ | `identify.csv` |

Example: user23's mixed hull vs user29's profile — pair point *i* of both for all 64 points, square the 64 gaps, add them, take the square root, divide by $\sqrt{64} = 8$ → **418.0 px**.

### Table 5

| Mixed hull ↓ / Profile → | user9 | user15 | user16 | user20 | user23 | user29 |
|---|---|---|---|---|---|---|
| user9 | **91.1** | 796.7 | 394.0 | 384.3 | 420.1 | 523.7 |
| user15 | 650.8 | **462.4** | 818.8 | 539.5 | 591.0 | 854.5 |
| user16 | 693.2 | **466.9** | 612.6 | 532.9 | 514.6 | 637.1 |
| user20 | 353.6 | 624.8 | 463.6 | **2.2** | 257.5 | 484.5 |
| user23 | 345.1 | 720.8 | 422.3 | 283.7 | **122.1** | 418.0 |
| user29 | 538.8 | 872.3 | 291.4 | 484.3 | 418.1 | **7.6** |
| user35 | 503.7 | 627.7 | **312.0** | 450.7 | 431.0 | 446.1 |
| user7 | 620.4 | 760.4 | **275.9** | 546.1 | 481.0 | 372.7 |

**Table 5.** Euclidean distance (RMS gap per point, px) between each user's mixed hull (rows) and each enrolled profile (columns). Bold = smallest value in the row (nearest profile).

### Worked calculation: user23 and user29 in Table 5

The four cells of Table 5 where user23 and user29 meet. Each compares one mixed hull (64 points, `concave_hull_mixed_0.5s/<user>/data_points.csv`) with one profile (64 points, `concave_hull_0.5s/<user>/data_points.csv`).

| Mixed hull | Profile | Gap at point 0 (px) | Largest gap | Smallest gap | $\sum g_i^2$ (px²) | $d = \sqrt{\sum g_i^2}$ (px) | $d_{RMS} = d / 8$ (px) |
|---|---|---|---|---|---|---|---|
| user23 | user23 (own) | 0.0 | 271.0 (point 22) | 0.0 (point 0) | 954,839 | 977.2 | **122.1** |
| user23 | user29 | 409.5 | 686.1 (point 33) | 103.3 (point 27) | 11,184,818 | 3,344.4 | **418.0** |
| user29 | user29 (own) | 0.0 | 20.5 (point 50) | 0.0 (point 0) | 3,722 | 61.0 | **7.6** |
| user29 | user23 | 409.5 | 679.6 (point 33) | 138.3 (point 13) | 11,187,572 | 3,344.8 | **418.1** |

| Cell | Calculation | Result | Meaning |
|---|---|---|---|
| user23 mixed → user23 profile | $\sqrt{954{,}839} = 977.2$; $977.2 \div 8$ | **122.1 px** | Nearest profile → user23 verified. The 14 strokes of failed sessions in the mixed hull widen its outline; largest gap 271.0 px at point 22, where the mixed hull (191.8, −3.9) sits inside the profile's (421.4, −147.8) |
| user23 mixed → user29 profile | $\sqrt{11{,}184{,}818} = 3{,}344.4$; $3{,}344.4 \div 8$ | **418.0 px** | Far: peak 686.1 px at point 33, user23 (−160.4, 11.3) vs user29's upward arm (−2.5, −656.4) |
| user29 mixed → user29 profile | $\sqrt{3{,}722} = 61.0$; $61.0 \div 8$ | **7.6 px** | Nearest profile → user29 verified. 18 of its 25 strokes are in the profile, so the outlines almost coincide (largest gap only 20.5 px) |
| user29 mixed → user23 profile | $\sqrt{11{,}187{,}572} = 3{,}344.8$; $3{,}344.8 \div 8$ | **418.1 px** | Far: peak 679.6 px at point 33, user29's upward arm (1.7, −664.1) vs user23 (−108.1, 6.6) |

Gap per point: $g_i = \sqrt{(\Delta x^{mixed}_i - \Delta x^{profile}_i)^2 + (\Delta y^{mixed}_i - \Delta y^{profile}_i)^2}$. Point 0 is the same for a user's mixed hull and profile (user23 (9, 361), user29 (410, 444)), so the own-profile gap at point 0 is 0; across users it is $\sqrt{(9 - 410)^2 + (361 - 444)^2} = 409.5$ px.

Result: each user is about 7–50 times closer to its own profile (122.1 and 7.6 px) than to the other's (418.0 and 418.1 px), so both are identified correctly.

### Identification result

| User | Role | Nearest profile | Distance (px) | Own profile distance (px) | Verified |
|---|---|---|---|---|---|
| user9 | legitimate | user9 | 91.1 | 91.1 | yes |
| user15 | legitimate | user15 | 462.4 | 462.4 | yes |
| user20 | legitimate | user20 | 2.2 | 2.2 | yes |
| user23 | legitimate | user23 | 122.1 | 122.1 | yes |
| user29 | legitimate | user29 | 7.6 | 7.6 | yes |
| user16 | impostor | user15 | 466.9 | 612.6 | no |
| user35 | impostor | user16 | 312.0 | — | no |
| user7 | impostor | user16 | 275.9 | — | no |

All five legitimate users were nearest to their own profile; no impostor was nearest to its own profile. user15's own distance (462.4 px) is close to user16's distance to user15's profile (466.9 px), because only 9 of user15's sessions passed.

## Notes

- All values match Table 4: user23 564,836 / 42 / 217,090 / 38.4%; user29 782,606 / 52 / 301,594 / 38.5%.
- $l_{min}$ = 1.0 px for both users because some recorded points are only 1 px apart, so the edge limit depends mostly on the longest edge (771.7 vs 991.7 px).
- Step 1 counts recorded points (196, 192); step 3 uses distinct points (169, 166), since every stroke starts at (0,0) and repeated points count once.
- At point 33, user29's outline is at the top of its upward arm (Δy −664) while user23's is near the middle (Δy 11.3), which gives the largest gap.
- The mixed hulls include impostor-tested strokes: 14 of user23's 25 and 7 of user29's 25 sessions did not pass.
- The mixed-to-mixed distance (3,337 px, 417 px per point) was computed from each mixed hull's `data_points.csv`; the notebook figures `user23_vs_user29.png` and `user23_vs_user29_steps.png` still show the profile comparison (3,353 px, 419 px).
- Steps 1–6 are feature extraction (Objective 3); step 7 is matching (Objective 4).
