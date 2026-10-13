# `03_chunk_shapes.py`: cut sessions into strokes and normalize their shapes

[← index](README.md) · previous: [02](02_sample_sessions.md) · next: [04](04_match_shapes.md)

## What it does

Step 3 of the single trial, and the core preprocessing of the whole experiment. Scripts 04, 06, 09, 10, 11, 12,
14 and 15 call its functions directly. It turns a long session (thousands of mouse events) into many short
**strokes** (chunks), then turns each stroke into a **normalized shape** that can be compared with any other
stroke, from any user, on any screen.

Outputs:

- `shapes/<class>/<user>/<session>.npz`: the raw strokes, as (x, y, t) points, plus a meta table
  (kind, path length in px, duration in s);
- `shapes/legitimate/<user>/library.npz`: every normalized move and drag shape of the user, which forms the
  user's **library**.

## Step 1: segmentation (`segment`)

**Algorithm**

```
click  ← rows whose state is Pressed or Released
points ← all other rows (Move and Drag), as (x, y, t)
a new stroke starts at point i when
      t_i − t_{i−1} > pause_gap_s            (the hand paused)
   or a click happened between point i−1 and point i
keep a stroke only if
      it has ≥ min_points points            (otherwise it is jitter)
  and its path length L ≥ min_length_px
kind ← DRAG if more than half its points are Drag, else MOVE
```

In formulas, with $\tau$ = `pause_gap_s` and $c_i$ = number of clicks up to row $i$:

$$\text{new stroke at } i \iff (t_i - t_{i-1} > \tau) \;\lor\; (c_i > c_{i-1})$$

$$L = \sum_{i=1}^{m-1} \sqrt{(x_{i+1}-x_i)^2 + (y_{i+1}-y_i)^2} \qquad\text{(path length)}$$

**Why pauses and clicks?** Mouse movement comes in bursts. People move toward a target, stop, click, and start
the next movement. A pause or a click marks where one intention ends and the next begins, so a stroke is roughly
one aimed movement. This follows the adviser's scope (2026-08-31): capture mannerisms from **short** signals,
not whole sessions. A pause threshold is the simplest segmentation rule that needs no labels and no model.

**Why remove click rows from the points?** A press or release usually repeats the last position. It marks a
boundary, not a movement.

**Why `min_points`?** Strokes with very few points are mostly hand tremor or a pointer nudge. They carry no
shape, and as tiny shapes they would match almost anything.

**Why separate move and drag?** Dragging (button held) is a different motor task from free movement: it is
slower, more careful, and often straight. Comparing a drag with a move would mix two behaviours.

## Step 2: normalization (`normalize`)

Each stroke is changed so that only its **shape** is left. Its position on the screen, its size, and its
sampling rate are removed.

**Algorithm**, with stroke points $p_1, \dots, p_m$ and $n$ = `resample_n` (64):

1. **Translate**: move the start to the origin, $p_i' = p_i - p_1$.
2. **Scale**: divide by the diagonal of the bounding box,
   $$D = \sqrt{(\max x' - \min x')^2 + (\max y' - \min y')^2}$$
   After this the stroke's bounding box has diagonal 1.
3. **Resample by arc length**: compute the cumulative distance along the path,
   $$s_1 = 0, \qquad s_i = s_{i-1} + d(p_{i-1}', p_i')$$
   Then place $n$ points at equal distances $s = 0, \tfrac{L}{n-1}, \tfrac{2L}{n-1}, \dots, L$ along the path,
   using **linear interpolation** (`np.interp`) between the recorded points.
4. Strokes with $D = 0$ or $L = 0$ (all points identical) cannot be normalized and are skipped. They still count
   in `n_chunks`, the denominator of the session's match ratio.

The result is an $n \times 2$ array, the same size for every stroke.

**Why each step:**

| Step | Removes | Why we need that |
|---|---|---|
| Translate | where on the screen the stroke happened | the same gesture at a different place is the same mannerism |
| Scale by the diagonal | how big the stroke is | screens range from 1280×800 to 1920×1080, so raw sizes partly measure the monitor |
| Arc-length resampling | how many points were logged, and how fast | user7/9/20 log every ~16 ms and the others every ~110 ms; a slow stroke has more points than a fast one |
| Fixed $n$ | different lengths | DTW (script 04) compares two arrays point by point |

**Why the diagonal, not width and height separately?** Dividing x by the width and y by the height would turn
every stroke into a square-ish shape and destroy its aspect ratio. A flat horizontal swipe and a diagonal swipe
would then look alike. One scale factor for both axes keeps the proportions.

**Why no rotation normalization?** Direction is part of the behaviour: someone who tends to move up-left
differs from someone who moves down-right. Rotating every stroke to a standard direction would throw that
information away.

**Why resample by arc length and not by time?** Arc-length spacing describes the path's geometry, independent
of speed. Speed is a separate signal, used as a feature in script 11.

## Step 3: per-user library (`describe`, `main`)

`describe()` stores each session's normalized shapes as a `Session` (key, number of strokes, and an
$(m, n, 2)$ array per kind). For a legitimate user, `main()` stacks the shapes of all their sessions into
`library.npz` (`move`, `drag`). The library is the user's profile for shape matching.

## Settings used

`pause_gap_s` (0.5 s), `min_points` (10), `min_length_px` (0 = off), `resample_n` (64).

## What we learned

Most strokes, after normalization, are close to a straight line from the start to the target. That makes many
strokes of different users look alike (see 04 and 14), which is the main limit of shape matching on Balabit.
