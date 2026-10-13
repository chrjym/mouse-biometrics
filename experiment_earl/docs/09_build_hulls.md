# `09_build_hulls.py`: convex and concave hulls of each user's stroke movements

[← index](README.md) · next: [10](10_hull_anomaly.md)

## What it does

For every user (all 10), it summarizes **where the user's strokes go** as one region in the plane. Each stroke
becomes one point, its net movement, and the hull around all those points is the user's "movement region".
This is Earl's original idea, and the profile used by the anomaly test in [10](10_hull_anomaly.md).

Outputs: `runs/<run>/hulls/<user>.json` (hull coordinates, areas, session list), `hulls/summary.csv`,
`figures/hulls/<user>.png`, `figures/hulls/all_users.png`.

## Algorithm

```
for each user:
    sessions ← first sessions_per_user sessions of session_pool(user, seed)   (same order as the notebook)
    points   ← []
    for each session: for each stroke from segment() (script 03):
        points.append( last point − first point )          # = (dx, dy)
    cloud    ← distinct points (np.unique)
    convex   ← convex hull of cloud
    concave  ← concave_hull(cloud, ratio = concave_ratio)
    save areas, coordinates, figure
```

### Step 1: one point per stroke, its displacement

Shift the stroke so it starts at $(0, 0)$. Its end point is then

$$e = (\Delta x, \Delta y) = (x_m - x_1,\; y_m - y_1)$$

This vector holds the stroke's **direction** and **distance**. Its length $\|e\| = \sqrt{\Delta x^2 + \Delta y^2}$
is reported as `median_distance_px`.

**Why only the end point?** It is the simplest summary of a stroke, and it captures two habits:

- the directions a user tends to move in (which depend on how they lay out windows and where they put their hand);
- how far they move in one go before pausing.

An earlier version hulled every point of every stroke (commits `359adb5`, `078c06c`). It was replaced at the
user's request, because the hull then mostly measured the screen size.

### Step 2: convex hull

The **convex hull** is the smallest convex polygon that contains all points: the shape a rubber band takes when
stretched around them. Shapely computes it with GEOS, which uses the **Graham scan** ($O(N \log N)$):

1. Take the lowest point as an anchor.
2. Sort the other points by angle around it.
3. Walk through them in that order, keeping a stack, and drop any point where the path turns the wrong way
   (a clockwise turn, decided by the sign of a cross product).

$$\text{cross}(o, a, b) = (a_x - o_x)(b_y - o_y) - (a_y - o_y)(b_x - o_x)$$

### Step 3: concave hull

A convex hull also covers large empty areas between groups of points, for example between "left moves" and
"down moves". Those empty areas would wrongly count as "typical for this user". The **concave hull** follows the
points more tightly.

GEOS builds it like this:

1. Compute the **Delaunay triangulation** of the points: triangles whose circumcircles contain no other point.
2. Repeatedly remove **border triangles** whose outer edge is longer than a length threshold:
   $$\ell_\text{max} = \ell_\text{min} + \texttt{concave\_ratio} \times (\ell_\text{longest} - \ell_\text{shortest})$$
   where the lengths are those of the triangulation's edges.
3. The remaining triangles form the hull.

`concave_ratio = 1` gives the convex hull, and `0` gives the tightest outline. We use 0.1. Duplicate points are
removed first (`np.unique`), because the triangulation needs distinct points.

### Step 4: area

Both hull areas come from the polygon's vertices $(x_1, y_1), \dots, (x_K, y_K)$ with the **shoelace formula**:

$$A = \frac{1}{2}\left|\sum_{i=1}^{K} \big(x_i\, y_{i+1} - x_{i+1}\, y_i\big)\right|, \quad (x_{K+1}, y_{K+1}) = (x_1, y_1)$$

`concave_share_of_convex` = concave area / convex area shows how much of the convex hull is empty space.

## Settings used

`sessions_per_user`, `seed`, `concave_ratio`, plus the segmentation settings of 03.

## What we learned (5 sessions, ratio 0.1)

- Convex hull areas are 3.0–7.2 million px². Concave hulls cover 59–81% of the convex area.
- The median stroke movement is 169–475 px.
- Hull extents still follow **screen size** (user15/16, on 1920×1080 screens, have the widest hulls), so area
  differences should not be read as behaviour without normalizing for the screen.
