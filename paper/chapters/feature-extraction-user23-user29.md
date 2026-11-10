# Feature Extraction: user23 vs user29

Run `19399f` (seed 945), split 5L × 1I, sensitivity 0.02, 25 sessions. Values are from the **profiles** (passed strokes only), 0.5 s strokes, concave ratio 0.15, 64 data points.

Figures: `experiment_earl/runs/19399f/hull_distance_0.5s/user23_vs_user29_steps.png` (steps 1–6) and `user23_vs_user29.png` (step 7). Notebook: `experiment_earl/notebooks/passed_strokes.ipynb`, sections 10.1 and 10.2.

## Methods used

| Stage | Method | Tool / source | Setting |
|---|---|---|---|
| Data | Balabit Mouse Dynamics Challenge dataset; sessions with `is_illegal = 1` removed | `datasets/balabit/users/` | 10 users; seed 945 draws the users and session order |
| Session screening | EARL shape matching: banded Dynamic Time Warping (DTW) between a session's strokes and the legitimate user's library | `earl_simulation.ipynb` → `runs/19399f/best/best_sessions.csv` | sensitivity 0.02, DTW band 0.1, session passes at ≥ 20% matched strokes, 25 sessions |
| Stroke segmentation | Pause-based segmentation; first stroke lasting ≥ 0.5 s, cut to exactly 0.5 s | `passed_strokes.ipynb` sections 3–4 | pause > 0.5 s or a click ends a stroke |
| Grouping | Profile = passed strokes; mixed hull = all tested strokes | sections 3–4 | this file uses the **profile** |
| Alignment | Translation to the origin | section 3 | $\Delta x = x - x_0,\ \Delta y = y - y_0$ |
| Convex hull | Graham scan | section 6 | cross product $(x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$ |
| Area | Shoelace formula | sections 6, 8 | $\frac{1}{2}\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\rvert$ |
| Concave hull | Delaunay triangulation with edge erosion (Davis) | section 8 (`scipy.spatial.Delaunay`) | ratio 0.15; $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| Data points | Fixed start (lowest corner, counter-clockwise) and arc-length resampling | section 9 | 64 points; $s_i = \frac{i}{64}P$ |
| Feature vector | Stacking point coordinates | section 9 | $H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$, 128 values |
| Comparison | Euclidean distance, reported as RMS gap per point | section 10 | $d = \sqrt{\sum g_i^2}$, $d_{RMS} = d / \sqrt{64}$ |
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

## Summary

| Steps | Value | user23 | user29 | Formula |
|---|---|---|---|---|
| Sessions | Sessions passed / registered | 11 / 25 | 18 / 25 | — |
| Align (0,0) | Strokes | 11 | 18 | $\Delta x_t = x_t - x_0, \quad \Delta y_t = y_t - y_0$ |
| | Recorded points | 116 | 152 | — |
| | Horizontal reach Δx (px) | −634 to 787 | −308 to 871 | $\min \Delta x,\ \max \Delta x$ |
| | Vertical reach Δy (px) | −231 to 361 | −689 to 444 | $\min \Delta y,\ \max \Delta y$ |
| Convex hull | Corners | 8 | 11 | $\mathrm{cross}(O,A,B) = (x_A - x_O)(y_B - y_O) - (y_A - y_O)(x_B - x_O)$ |
| | Area (px²) | 522,470 | 782,606 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| Concave hull | Edge limit L (px) | 118.7 | 149.6 | $L = l_{min} + 0.15(l_{max} - l_{min})$ |
| | Corners | 30 | 53 | edges $> L$ removed |
| | Area (px²) | 224,410 | 298,036 | $\frac{1}{2}\left\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\right\rvert$ |
| | Concave / convex | 43.0% | 38.1% | $\frac{Area_{concave}}{Area_{convex}} \times 100\%$ |
| Fixed start | Point 0 (Δx, Δy) | (9, 361) | (410, 444) | lowest corner, counter-clockwise |
| Data points | Perimeter P (px) | 3,975 | 4,863 | $P = \sum\sqrt{(x_{k+1} - x_k)^2 + (y_{k+1} - y_k)^2}$ |
| | Points | 64 | 64 | $s_i = \frac{i}{64}P, \quad i = 0, \dots, 63$ |
| | Spacing (px) | 62.1 | 76.0 | $\Delta s = \frac{P}{64}$ |
| Feature vector | Values | 128 | 128 | $H = (\Delta x_0, \Delta y_0, \dots, \Delta x_{63}, \Delta y_{63})$ |
| Euclidean distance | Gap per point | 409.5 (point 0) to 671.4 (point 33) | | $g_i = \sqrt{(\Delta x^A_i - \Delta x^B_i)^2 + (\Delta y^A_i - \Delta y^B_i)^2}$ |
| | Total distance (px) | 3,353 | | $d = \sqrt{\sum_{i=0}^{63} g_i^2}$ |
| | RMS gap per point (px) | 419 | | $d_{RMS} = \frac{d}{\sqrt{64}}$ |

Negative Δy is upward (screen coordinates).

## Computation

| Step | Value | How it is computed | user23 | user29 |
|---|---|---|---|---|
| **0. Sessions** | Passed / registered | A session passes when ≥ 20% of its strokes match the library (DTW, sensitivity 0.02) | 11 / 25 | 18 / 25 |
| **1. Align** | Strokes | One stroke per passed session: the first lasting ≥ 0.5 s, cut to 0.5 s | 11 | 18 |
| | Recorded points | All points of the strokes, pooled | 116 | 152 |
| | Aligned point | $\Delta x = x - x_0,\ \Delta y = y - y_0$ | e.g. (983, 217) → (0, 0) | each stroke's first point → (0, 0) |
| | Reach | min and max of Δx, Δy | Δx −634 to 787; Δy −231 to 361 | Δx −308 to 871; Δy −689 to 444 |
| **2. Convex hull** | Corners | Graham scan: lowest point = anchor, sort by angle, keep left turns (cross > 0) | 8 | 11 |
| | Area | Shoelace: $\frac{1}{2}\lvert\sum(x_k y_{k+1} - x_{k+1} y_k)\rvert$ | 522,470 px² | 782,606 px² |
| **3. Concave hull** | Triangles | Delaunay triangulation of the distinct points | 105 points → 200 triangles, 304 edges | 133 points → 252 triangles, 384 edges |
| | Edge limit L | $L = l_{min} + 0.15(l_{max} - l_{min})$ | 1.0 + 0.15 × (785.5 − 1.0) = **118.7 px** | 1.0 + 0.15 × (991.7 − 1.0) = **149.6 px** |
| | Corners | Outer triangles with edges longer than L removed, longest first | 30 | 53 |
| | Area | Shoelace on the concave outline | 224,410 px² | 298,036 px² |
| | Share of convex | concave ÷ convex | 224,410 ÷ 522,470 = **43.0%** | 298,036 ÷ 782,606 = **38.1%** |
| **4. Fixed start** | Point 0 | Lowest corner (largest Δy), leftmost if tied; then counter-clockwise | (9, 361) | (410, 444) |
| **5. Data points** | Perimeter P | Sum of the outline's edge lengths | 3,975 px | 4,863 px |
| | Spacing | $P \div 64$ | 3,975 ÷ 64 = **62.1 px** | 4,863 ÷ 64 = **76.0 px** |
| | Point positions | $s_i = \frac{i}{64}P$, i = 0 … 63 | every 62.1 px along the outline | every 76.0 px along the outline |
| **6. Feature vector** | Length | 64 points × (Δx, Δy) | 64 × 2 = **128** | 64 × 2 = **128** |

### Step 7: Euclidean distance between the two vectors

| Value | How it is computed | Result |
|---|---|---|
| Gap at point 0 | $g_0 = \sqrt{(9 - 410)^2 + (361 - 444)^2} = \sqrt{160{,}801 + 6{,}889}$ | **409.5 px** |
| Gap at point 33 (largest) | user23 (−108.1, 6.6) vs user29 (−2.5, −656.4): $\sqrt{105.6^2 + 663.0^2}$ | **671.4 px** |
| Sum of squared gaps | $\sum_{i=0}^{63} g_i^2$ | 11,241,785 px² |
| Total distance | $d = \sqrt{11{,}241{,}785}$ | **3,353 px** |
| RMS gap per point | $d \div \sqrt{64} = 3{,}353 \div 8$ | **419 px** |

## Notes

- $l_{min}$ = 1.0 px for both users because some recorded points are only 1 px apart, so the edge limit depends mostly on the longest edge (785.5 vs 991.7 px).
- Step 1 counts recorded points (116, 152); step 3 uses distinct points (105, 133), since every stroke starts at (0,0) and repeated points count once.
- At point 33, user29's outline is at the top of its upward arm (Δy −656) while user23's is near the middle (Δy 6.6), which gives the largest gap.
- Steps 1–6 are feature extraction (Objective 3); step 7 is matching (Objective 4).
