# Shape-only authentication: results (2026-10-17)

Can the **shape** of mouse strokes or sessions tell Balabit users apart? Six approaches, all on the same draw
(each user's shuffled session pool: first k sessions = profile, last k = own test, sessions k..2k of every other
user = impostor test), k = 4 unless noted, EER as mean ± std over seeds 945–949 (50% = chance).

| Method | What is compared | EER |
|---|---|---|
| DTW shape matching (sensitivity 0.04) | strokes, banded DTW (`runs/efdc92`) | ~43% |
| Euclidean on geometric measures | session medians of straightness, chord deviation, bow side, Menger curvature (mean, peak), overshoot, hull fill; z-scored | 43.3 ± 5.0% |
| Convex hull (DTW filter 0.06, rotated) | share of stroke points inside the user's core hull | 45.4 ± 1.1% |
| Pure Euclidean on stroke points | 64 points per stroke, nearest enrolled stroke, session median | 45.4 ± 2.6% |
| Direction star | median stroke per 8 directions, Euclidean between stars | 49.5 ± 4.8% |
| Density shape (k = 4 / 8) | 32×32 grid of stroke points (direction and screen-relative size kept), Euclidean on √density | 51.1 ± 6.4% / 50.0 ± 2.7% |

**Finding:** every approach lands at 43–51%. Who the user is explained only 0–3.4% of the variation of any geometric
measure; a user's own sessions differ from each other about as much as from other users'. Shape alone is at most a
weak signal on Balabit.

## Figures

- `direction_stars.png`: left, every user's profile star on one origin (nearly identical); grid, own (blue) vs other
  users' (red) session stars against the profile (black).
- `density_shapes.png`: same layout for the density shape (50% contour). user12 (vertical) and user21 (horizontal)
  are the only visibly distinct profiles, and their own sessions do not keep that shape.
- `density_explained.png`: how a session becomes a shape: strokes from (0, 0) → grid → contours.
- `euclidean_pairs_user29.png`: pure Euclidean, each test stroke joined point by point to its nearest enrolled
  stroke; own (blue) and impostor (red) gaps are the same size.

The scripts (`18_hull_profile.py`, `19_geometry.py`, `20_euclidean_strokes.py`, `21_session_star.py`,
`21_density_shape.py`) were removed after this summary; they are in git history.
