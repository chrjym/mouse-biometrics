# Stroke shapes of one user: from chained strokes to convex hulls

Exploration of 2026-10-18. Goal: form a shape for one specific user from that user's strokes, using the best sensitivity and session count found so far, and close it into a shape that can be described geometrically. Sections 1–5 describe how the shapes were built; section 6 compares two users; section 7 explains why the convex hull is used; section 8 tests 0.5 s pieces with the hull as the decision step.

Data: Balabit, merged user folders (`datasets/balabit/users/<user>/`). Main user: **user29**. Second user, same steps: **user20**.

## 1. Choosing the sensitivity and the session count

- Source: `runs/efdc92/accuracy.csv`, made by `src/16_plot_accuracy.py` over the batch runs `1_9_<sensitivity>_<sessions>` (seed 945, user29 legitimate against 9 impostors, sensitivity 0.02–0.80, 2–26 sessions).
- For every (sensitivity, sessions) pair: mean share of the legitimate user's sessions that pass, minus the mean share of impostor sessions that pass.
- Largest gap: **sensitivity 0.04, 4 sessions** (user29 0.57, impostors 0.44, gap 0.13). Above 0.06 nearly every session passes for every user.
- So the shapes use each user's **first 4 sessions** of their shuffled pool (`00_config.session_pool(config, user, 945)`), with the settings of `runs/efdc92/1_9_0.04_4/config.yaml. 

## 2. Strokes (chunks) of a session

Done by `segment()` in `src/03_chunk_shapes.py`, unchanged:

1. Read `client timestamp, button, state, x, y`; drop scroll rows and glitch rows (x or y = 65535); keep time order (stable sort).
2. Remove `Pressed`/`Released` rows; they only mark boundaries.
3. Start a new stroke after a time gap > **0.5 s** (`pause_gap_s`) or after any click.
4. Drop strokes with fewer than **10 points** (`min_points`); no length filter (`min_length_px: 0`).
5. Label a stroke *drag* if more than half of its points are `Drag`, else *move*. **Only move strokes are used.**

What is recorded per stroke: the raw `[x, y, t]` points, plus points, duration, path length, start and end position (`strokes.csv`, `stroke_points.csv`).

Note: 0.5 s is the pause that *ends* a stroke, not the stroke length. Median stroke durations are 1.15–1.75 s, so these strokes are longer than the ~0.5 s short strokes in the thesis scope.

| user | sessions (strokes each) | move strokes | recorded points | logging interval |
|---|---|---|---|---|
| user29 | 3 / 66 / 69 / 18 | 156 | 2,320 | ~110 ms |
| user20 | 115 / 25 / 40 / 16 | 196 | 8,686 | ~16 ms |

## 3. Shape-based views (normalized strokes)

### 3.1 Normalization
`normalize()` in `03_chunk_shapes.py`: shift the first point to **(0, 0)**, scale by the bounding-box diagonal (diagonal = 1), resample to 64 points evenly spaced along the path. Time and screen position are dropped.

### 3.2 Nearest-neighbour chain
- Pairwise distance between strokes: banded DTW (band = 0.1 × 64 points), mean distance per point, the same measure the experiment uses.
- Chain: start at the medoid (smallest summed distance), repeatedly step to the most similar unused stroke.
- Joining: each stroke is translated so it starts where the previous one ended.
- Result (`chain_user29.png`): the joined path curls into a loop because the order sorts strokes by **direction**. Only 28% of strokes have a neighbour within 0.04; 129 of 155 links are wider than 0.04.

### 3.3 Direction-free alignment
- Each stroke rotated so start → end lies on the +x axis, scaled so the start-to-end distance = 1, and mirrored so the bend points up. Every aligned stroke runs **(0, 0) → (1, 0)**.
- Strokes whose start-to-end distance is under 0.5 × their bounding-box diagonal end near their start (**loops**, 16 for user29) and are kept apart.
- Views (`shape_ways_user29.png`): mean stroke ± 1 sd; bend map (bulge = max height / chord, against where the bend peaks); families (the chain of aligned strokes cut at links > 0.04, runs of ≥ 3 strokes; 7 families covering 80 strokes); a straight-to-curved "alphabet".
- user29: median bulge 0.17, bend peaks ~2/3 along the stroke, 9% nearly straight.
- Chaining aligned strokes end to start gives only a straight line, since they all point the same way.

### 3.4 Closing the shape (aligned frame)
`closed_shapes_user29.png`:

| shape | how it is closed | area | perimeter |
|---|---|---|---|
| closed chain | chain end joined to its start by one straight line | 928.8 (stroke units) | 173.5 |
| convex hull | around all aligned points | 2.92 | 6.63 |
| concave hull | shapely `concave_hull`, ratio 0.15 | 1.73 | 8.47 |
| envelope | per x-slice, 10th–90th percentile of heights, lower edge + upper edge | 0.28 | 2.74 |

## 4. Pixel-space views (strokes shifted to (0, 0))

From here the strokes are **only translated**: every point minus the stroke's first point. No scaling, rotation or resampling, so real size (px) and on-screen direction are kept.

### 4.1 All strokes at (0, 0)
`all_strokes_origin_<user>.png`: all strokes overlaid from the origin.

### 4.2 Tools

All hulls are computed with **shapely 2.2.0**, which calls the **GEOS** geometry library. No hull algorithm was written by hand. The functions used are `MultiPoint(...).convex_hull`, `shapely.concave_hull`, `.intersection`, `shapely.union_all`, `.area` and `.length`.

#### Input point set

Stroke *s* has recorded points (xᵢ, yᵢ), i = 0 … nₛ − 1. Each point is shifted by the stroke's first point:

  x′ᵢ = xᵢ − x₀  y′ᵢ = yᵢ − y₀

The point set P is the union of the shifted points of all strokes of the user (user29: 2,320 points; user20: 8,686). Hulls are built from these **recorded points only**, not from the line segments between them. For a sparse logger (user29, ~110 ms) a hull edge can therefore cross empty space between two recorded points.

### 4.3 Convex hull

**Definition.** The convex hull CH(P) is the smallest convex polygon that contains every point of P. All interior angles are < 180°, so it has no dents. Equivalently, it is the set of all convex combinations of points of P:

  CH(P) = { Σ λᵢ pᵢ | λᵢ ≥ 0, Σ λᵢ = 1 }

**Algorithm (Graham scan, as used by GEOS).**

1. Take the point with the lowest y as the pivot. (In GEOS, ties are broken by x, and points inside a bounding octagon are removed first to save time.)
2. Sort the remaining points by polar angle around the pivot.
3. Walk through the sorted points, keeping a stack of hull vertices. For the last two stack points a, b and the next point c, compute the cross product

  cross(a, b, c) = (bₓ − aₓ)(c_y − a_y) − (b_y − a_y)(cₓ − aₓ)

   - cross > 0: a left turn, so push c.
   - cross ≤ 0: a right turn or collinear, so pop b and test again.
4. The stack that remains is the hull, in counter-clockwise order.

Cost: O(n log n), dominated by the sort.

**Degenerate case.** If all points lie on one line, the hull is a line segment with area 0, not a polygon. This happened for 1 of user20's 196 strokes in 4.5, and that stroke was skipped.

### 4.4 Concave hull

**Why.** The convex hull bridges every dent with a straight edge, so empty space between stroke directions counts as part of the shape. A concave hull follows the points inward.

**Algorithm (`shapely.concave_hull(P, ratio=r)`, GEOS `ConcaveHull`, edge-length variant).** The idea comes from the "χ-shape" of Duckham et al. (2008). That paper is outside the thesis's 2021–2026 citation range, so treat it as the method's origin and check with the adviser before citing it.

1. **Delaunay triangulation** of P. The points are joined into triangles so that no point lies inside any triangle's circumscribed circle. The outer boundary of the triangulation is exactly the convex hull.
2. **Edge-length threshold.** Let L_min and L_max be the shortest and longest edge lengths in the triangulation. Then

  L = L_min + r · (L_max − L_min),  0 ≤ r ≤ 1

   - r = 0 gives the tightest hull (only the shortest edges may stay on the boundary).
   - r = 1 keeps every edge, which is the convex hull.
3. **Erosion.** Repeatedly take a triangle on the outer boundary whose outer edge is longer than L, and remove it. It is removed only if the result stays **one simple polygon** (no holes, no split into pieces). The default `allow_holes=False` is used.
4. Stop when no removable boundary triangle has an outer edge longer than L. The remaining boundary is the concave hull.

Long Delaunay edges span empty regions, so removing them pulls the outline in toward the strokes. A lower r removes more triangles.

**Ratios used.** r = 0.05, 0.15 and 0.3 (`concave_hull_origin_<user>.png`). **r = 0.15** was chosen as the working value because:

- r = 0.05 follows single strokes into thin arms (user29: 41% of the convex area, perimeter 14,877 px);
- r = 0.3 is close to convex (75%);
- r = 0.15 keeps the main reach directions with dents between them (63%).

### 4.5 Convex hulls added to the concave hull

**a. Convex hull of all strokes.** CH(P) as in 4.3, drawn dashed around the concave hull.

**b. Nested convex hulls by reach.** For each stroke, the reach is how far it gets from its start:

  reachₛ = maxᵢ √(x′ᵢ² + y′ᵢ²)

For each level q ∈ {50, 75, 90, 100}%:

  S_q = { s | reachₛ ≤ percentile_q(reach) },  H_q = CH(points of strokes in S_q)

The percentile uses numpy's default linear interpolation. The hulls are nested (H₅₀ ⊆ H₇₅ ⊆ H₉₀ ⊆ H₁₀₀) and show how the outline grows as longer strokes are added (`hulls_origin_<user>.png`).

**c. Per-stroke convex hulls.** One hull per stroke, Hₛ = CH(points of s), drawn inside the hulls of all strokes (`stroke_hulls_origin_<user>.png`). A near-straight stroke gives a thin wedge from (0, 0); a curved or turning stroke gives a wide hull.

### 4.6 Measures

For a polygon with vertices (x₁, y₁) … (x_m, y_m), where (x_{m+1}, y_{m+1}) = (x₁, y₁):

| Measure | Formula |
|---|---|
| Area (shoelace) | A = ½ · \| Σᵢ (xᵢ·yᵢ₊₁ − xᵢ₊₁·yᵢ) \| |
| Perimeter | Σᵢ √((xᵢ₊₁ − xᵢ)² + (yᵢ₊₁ − yᵢ)²) |
| Concave share of convex | A(concave) / A(CH(P)) |
| Nested hull inside concave | A(concave ∩ H_q) / A(H_q) |
| Union of per-stroke hulls | A(H₁ ∪ H₂ ∪ … ∪ Hₙ) / A(concave) |
| Per-stroke hull size | median, 90th percentile and maximum of A(Hₛ) |

Units are px for lengths and px² for areas. ∩ (intersection) and ∪ (`union_all`) are polygon operations computed by GEOS.

## 5. Results (px²)

| | user29 | user20 |
|---|---|---|
| median / max reach | 297 / 1,100 px | 329 / 1,790 px |
| convex hull, all strokes | 1,987k | 3,875k |
| concave hull 0.15 | 1,244k | 2,251k |
| convex hull, shortest 50% | 240k | 280k |
| convex hull, shortest 75% | 535k | 824k |
| convex hull, shortest 90% | 1,046k | 1,876k |
| share of 90% hull inside concave hull | 88% | 83% |
| per-stroke hull median / max | 11k / 407k | 11k / 740k |
| union of per-stroke hulls / concave hull | 99% | 100% |

Observations:
- The core (shortest 50% of strokes) is compact and nearly round for both users, and similar in size.
- The last 10% of strokes (the longest) roughly double the convex hull; they set the outer corners and the empty space.
- The concave hull is close to the union of the per-stroke convex hulls.
- Most per-stroke hulls are thin wedges from (0, 0) (near-straight strokes); wide ones come from curved or turning strokes.

## 6. Comparing two users (user29 vs user20)

Script: `runs/efdc92/compare_fair/compare_fair.py` (outputs `pairs.csv`, `summary.csv`, `compare_fair_metrics.png`, `compare_fair_shapes.png` in the same folder).

### 6.1 Making sessions comparable
1. **Sessions:** the first 8 sessions of each user's shuffled pool (seed 945). Sessions with fewer than 15 usable strokes are skipped (user29: 2 skipped, leaving 6; user20: 8).
2. **Same stroke count:** 15 move strokes drawn at random from each session (`Random("945-<user>-strokes")`).
3. **Screen scale:** coordinates divided by the user's screen size, estimated as the largest x and y over all of the user's sessions (both ≈ 1920 × 1080).
4. **Same point spacing:** every stroke shifted to (0, 0) and resampled along its path every 0.01 screen units, so the 16 ms and 110 ms loggers give comparable outlines.
5. **Hulls per session:** the 90% convex hull (strokes up to the 90th percentile of reach) and the concave hull (r = 0.15), built from the resampled points.

### 6.2 Measures per pair of sessions
- **Stroke Fréchet:** strokes aligned as in 3.3 and resampled to 32 points. For every stroke, the discrete Fréchet distance to the nearest stroke of the other session; the mean over both directions:
  d(A, B) = ½ [ mean_{a∈A} min_{b∈B} d_F(a, b) + mean_{b∈B} min_{a∈A} d_F(a, b) ]
  with c(i,j) = max(‖pᵢ − qⱼ‖, min(c(i−1,j), c(i−1,j−1), c(i,j−1))), d_F = c(n,m).
- **Hull IoU:** A(A ∩ B) / A(A ∪ B), for both hull types.
- **Outline Fréchet:** both outlines oriented counter-clockwise, resampled to 120 points, d_F computed for every start point of B; the smallest is kept.

### 6.3 Decision rule
Pairs are grouped as **within user29** (15), **within user20** (28) and **between** (48). The users are distinct only if between-user pairs are less alike than within-user pairs. This is summarized as an AUC: the chance that a random between-user pair is less alike than a random within-user pair (0.5 = no difference, 1.0 = fully distinct).

### 6.4 Result

| measure | within user29 | within user20 | between | AUC |
|---|---|---|---|---|
| stroke Fréchet (lower = alike) | 0.160 | 0.176 | 0.170 | 0.48 |
| 90% convex hull IoU (higher = alike) | 0.471 | 0.415 | 0.437 | 0.54 |
| concave hull IoU | 0.286 | 0.255 | 0.236 | 0.61 |
| 90% convex outline Fréchet (screen units) | 0.178 | 0.284 | 0.251 | 0.55 |
| concave outline Fréchet (screen units) | 0.230 | 0.401 | 0.352 | 0.57 |

- All AUCs are 0.48–0.61, near chance: after the fairness fixes, user29 and user20 are **not distinct** by these measures.
- Stroke shape (Fréchet on aligned strokes) shows no difference at all (AUC 0.48).
- The hulls show a small effect (best: concave IoU, 0.61). It comes mostly from user29 being more consistent than user20 (user29's within-user outline Fréchet 0.18–0.23 vs user20's 0.28–0.40), not from the two users being apart; between-user values fall between the two.
- Limits: two users only; 15 strokes per session is small; the 15 strokes are one random draw.

## 7. Why the convex hull is used

### 7.1 Reasons
1. **It closes the shape.** Strokes are open lines; the convex hull is the smallest closed convex outline that contains all of them, so a user's movement becomes one region with an area, a perimeter and a boundary.
2. **It is fully geometric and explainable.** It is computed by a fixed algorithm (Graham scan, 4.3) and measured with closed formulas (shoelace area, perimeter, compactness 4πA/P²). No training and no black-box model, in line with the study's geometric focus.
3. **It has no setting to tune.** The same points always give the same hull. The concave hull depends on the ratio r (0.15, chosen by eye); the convex hull does not.
4. **It gives a boundary for decisions.** In continuous authentication a new stroke can be tested against the user's region (inside, or how far outside). A convex region makes this test simple and fast.
5. **It is stage 3 of the proposed method:** short strokes → closed-form geometry → **convex hull bounding** → Discrete Fréchet distance → dynamic trust threshold. Using it keeps the study consistent with the proposal.
6. **It is easy to show and check.** A hull drawing can be checked by eye by the adviser and readers.

### 7.2 What the results say about it
- **Short window (a few strokes or one session):** the hull still has a direction and an outline (sections 4–5, `session_shapes_user29_user20.png`).
- **Per-session hulls do not separate user29 from user20:** AUC 0.54–0.57 (section 6). A session's hull reflects how many strokes the session has more than who made them.
- **Whole data (every session):** script `runs/efdc92/compare_explained/whole_hulls.py`, figure `whole_hulls_user29_user20.png`, numbers `whole_hulls.csv`. Every move stroke of every session, moved to (0, 0): user29 124 sessions / 8,928 strokes, user20 114 sessions / 9,748 strokes. (The shaded concave hull uses a random sample of 60,000 points per user.)

| convex hull around | user29 | user20 | IoU |
|---|---|---|---|
| shortest 50% of strokes | 296k px² | 240k px² | 0.81 |
| shortest 75% | 763k px² | 758k px² | 0.99 |
| shortest 90% | 1,625k px² | 1,727k px² | 0.94 |
| all strokes | 7,352k px² | 6,911k px² | 0.87 |

  - The 50–90% hulls become circles (compactness 0.99 for both); direction habits seen in 4 sessions disappear.
  - The 100% hull spans about ±1,900 × ±1,050 px, i.e. the 1920 × 1080 screen both users have: it measures the monitor, not the person.
  - The only remaining difference is the core size (user29 ~20% larger; median reach 310 vs 279 px).

### 7.3 Role in the method
> The convex hull is used to bound a user's short-stroke trajectories into a closed, measurable region (area, perimeter, compactness, reach), giving a geometric and explainable representation and a boundary for the decision stage.

It is a **bounding and measuring step**, not an identifier on its own: in these tests the hull of one session reflected the window size and the screen more than the user.

## 8. Short strokes (0.5 s pieces) as the decision step

Strokes in sections 2–7 last 1.15–1.75 s (median), longer than the ~0.5 s scope. Here every move stroke is cut into 0.5 s pieces and the hull is used as the decision boundary (section 7.3).

### 8.1 Steps
1. **Cut**: within a move stroke with times t_0…t_m, point i goes to piece ⌊(t_i − t_0) / 0.5⌋. Pieces with fewer than 4 points or no extent are dropped.
2. **Shift**: each piece is moved so its first point is (0, 0): (x_i − x_0, y_i − y_0). No scaling or rotation.
   Check: every piece lasts ≤ 0.5 s (median 0.42 s user29, 0.44 s user20; max 0.499 s). Figure: `short_strokes/all_pieces_origin_user29_user20.png`.
3. **Enrol**: all points of the pieces from the user's first 4 pool sessions → concave hull (ratio 0.15) and convex hull = the user's region R.
4. **Test**: each of the last 4 pool sessions of both users. A piece counts as inside if at least 90% of its points lie in R:
   inside(piece) = [ (1/n) Σ 1(p_i ∈ R) ≥ 0.9 ],  score(session) = mean of inside over its pieces.
5. **Decide**: accept when the score is high; a rule works only if own sessions score above the other user's.

### 8.2 Regions

| user | enrolment pieces | median reach | points per piece | concave 0.15 | convex |
|---|---|---|---|---|---|
| user29 | 332 | 121 px | 5 | 980k px² | 1,687k px² |
| user20 | 541 | 92 px | 15 | 1,234k px² | 1,797k px² |

Concave-region IoU user29 vs user20: **0.37** (whole-data long strokes: 0.81–0.99), so short pieces make the regions more different.

Section 4 figures redone with the 0.5 s pieces (same steps, `_0.5s` suffix, next to the full-stroke ones):
`all_strokes_origin_<user>_0.5s.png`, `concave_hull_origin_<user>_0.5s.png`, `hulls_origin_<user>_0.5s.png`, `stroke_hulls_origin_<user>_0.5s.png`, `strokes_0.5s.csv`, `stroke_points_0.5s.csv`, `strokes_0.5s/` (one PNG per piece), in `shapes_explore/` (user29) and `shapes_explore_user20/`.

| 0.5 s pieces | user29 | user20 |
|---|---|---|
| nested convex 50% / 75% / 90% / 100% | 35k / 156k / 352k / 1,687k px² | 21k / 129k / 445k / 1,797k px² |
| per-piece convex hull, median | 1k px² | < 1k px² |

### 8.3 Scores (share of pieces inside the concave region)

| region | own test sessions | other user's test sessions |
|---|---|---|
| user29 | 0.90–0.96 | 0.83–0.92 |
| user20 | 0.91–0.98 | 0.93–1.00 |

- Against user29's region the other user scores slightly lower: weak separation.
- Against user20's region it fails: user29's short, sparse pieces fit inside the larger region more often than user20's own.
- Every score is ≥ 0.83: a short piece near (0, 0) lands inside almost any region, so "inside or not" alone is a weak rule.

### 8.4 Meaning
Short pieces change the region shape between users, but the inside-share does not separate them. The next step is to describe each 0.5 s piece by its shape (direction, curvature, bend, reach) and use the hull as the boundary in that shape space.

Figures and data: `runs/efdc92/short_strokes/` (`short_strokes_regions.png`, `short_strokes_scores.png`, `regions.csv`, `scores.csv`).

## 9. Limits

- Two users, 4 sessions each; session sizes are uneven (user29 has a 3-stroke session, user20 a 115-stroke one).
- Pixel shapes mix behaviour with hardware: screen size and logging rate differ by user (110 ms vs 16 ms), so outlines of user29 are coarser and partly drawn through empty space between sparse points.
- Hulls are built from recorded points, not the segments between them, so sparse logging lets edges cross empty space.
- The concave hull depends on the chosen ratio r; 0.15 is a visual choice, not a fitted value.
- Hulls are pulled by single long strokes; the 90% hull or the concave hull at 0.15 are less sensitive to them.
- Strokes in sections 2–7 are longer than the ~0.5 s scope; the 0.5 s pieces of section 8 have only ~5 points for user29 (110 ms logging).
- Test sessions are uneven (one user29 test session has 1,315 pieces, others 32–139).

## 10. Files and how to rerun

Scripts (copied from the session scratchpad) are in `scripts/`; run from the repo root with the venv:

```bash
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/chain_shape.py     # 3.2 chain
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/shape_ways.py      # 3.3 aligned views
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/closed_shapes.py   # 3.4 closed shapes
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/export_strokes.py  # user29 strokes, CSVs
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/user_hulls.py user20  # section 4 for any user (add 0.5 for 0.5 s pieces)
.venv/bin/python experiment_earl/runs/efdc92/shapes_explore/scripts/session_shapes.py   # one panel per session, user29 and user20
.venv/bin/python experiment_earl/runs/efdc92/compare_fair/compare_fair.py                # section 6 comparison
.venv/bin/python experiment_earl/runs/efdc92/compare_explained/whole_hulls.py          # section 7.2 whole-data hulls
.venv/bin/python experiment_earl/runs/efdc92/short_strokes/short_strokes.py          # section 8 short strokes
.venv/bin/python experiment_earl/runs/efdc92/short_strokes/pieces_origin.py          # section 8 pieces at (0,0) + duration check
```

Section 4 for user29 was drawn inline; `user_hulls.py user29 0.5` writes the 0.5 s version into `runs/efdc92/shapes_explore/`; do not run `user_hulls.py user29` without 0.5 there, it would overwrite `strokes.csv`, which also holds the chain columns from `export_strokes.py`. The `runs/` folder is git-ignored, so these files are not committed.
