# `07_plot_shapes.py`: draw every stroke as an image

[← index](README.md)

## What it does

Draws every stroke saved by script 03 as a small PNG, so we can **see** what the matcher compares. Per session
it also draws `overview.png`, a 10 × 10 grid of the first 100 strokes.

Output: `runs/<run>/shapes/<class>/<user>/<session>/chunk_<i>_<move|drag>.png` and `overview.png`.

## Algorithm

```
saved ← every shapes/*/*/session_*.npz of the run           (needs steps 01–03 first)
keep only --user users, if given
in parallel (multiprocessing Pool, --workers processes), per session file:
    load the raw strokes (load_chunks from 03)
    for each stroke (at most --limit):
        draw the raw screen path; blue = move, orange = drag
        green dot = start, red dot = end
        title: index, kind, path length in px, duration in s
        save as PNG
    unless --no-overview: draw the first 100 strokes in one grid
```

## Choices

- **Raw strokes, not normalized ones.** The PNGs show the strokes as they were on screen, in pixels. This makes
  logging problems (jumps, glitches, tiny jitter strokes) easy to spot, which a normalized shape would hide.
- **Inverted y axis.** Screen coordinates grow downward. `invert_yaxis()` makes the picture look like the
  screen.
- **Equal aspect.** One pixel in x has the same length as one pixel in y, so curves are not distorted.
- **Parallel workers.** A run can hold tens of thousands of strokes. Each session is independent, so several
  processes can plot at once.

This script computes nothing new: it is a visual check of segmentation (03).
