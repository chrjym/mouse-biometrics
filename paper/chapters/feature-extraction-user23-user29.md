# Feature Extraction: user23 vs user29

Run `19399f` (seed 945), split 5L × 1I, sensitivity 0.02, 25 sessions. Values are from the **profiles** (passed strokes only), 0.5 s strokes, concave ratio 0.15, 64 data points.

Figures: `experiment_earl/runs/19399f/hull_distance_0.5s/user23_vs_user29_steps.png` (steps 1–6) and `user23_vs_user29.png` (step 7). Notebook: `experiment_earl/notebooks/passed_strokes.ipynb`, sections 10.1 and 10.2.

## Summary

| Step | Value | user23 | user29 |
|---|---|---|---|
| 0. Sessions | Sessions passed / registered | 11 / 25 | 18 / 25 |
| 1. Align at (0,0) | Strokes | 11 | 18 |
| | Recorded points | 116 | 152 |
| | Horizontal reach Δx (px) | −634 to 787 | −308 to 871 |
| | Vertical reach Δy (px) | −231 to 361 | −689 to 444 |
| 2. Convex hull | Corners | 8 | 11 |
| | Area (px²) | 522,470 | 782,606 |
| 3. Concave hull | Edge limit L (px) | 118.7 | 149.6 |
| | Corners | 30 | 53 |
| | Area (px²) | 224,410 | 298,036 |
| | Concave / convex | 43.0% | 38.1% |
| 4. Fixed start | Point 0 (Δx, Δy) | (9, 361) | (410, 444) |
| 5. Data points | Perimeter (px) | 3,975 | 4,863 |
| | Points | 64 | 64 |
| | Spacing (px) | 62.1 | 76.0 |
| 6. Feature vector | Values | 128 | 128 |
| 7. Euclidean distance | Total distance (px) | 3,353 | |
| | RMS gap per point (px) | 419 | |
| | Largest gap | 671 px at point 33 | |

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
