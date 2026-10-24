# `17_plot_sweep.py`: figures of the sensitivity sweep

[← index](README.md) · previous: [16](16_sweep_sensitivity.md)

## What it does

Reads `runs/<hash>/sweep/confusion.csv` and `best.csv` (written by [16](16_sweep_sensitivity.md)) and draws four
figures into the same folder. Takes an optional hash (default: the one `config.yaml` selects).

- `accuracy_vs_sensitivity.png`: one panel per split; balanced accuracy against sensitivity, one line per library
  size of 1, 10, 20 and 40 sessions (light to dark blue), the grey band = lowest to highest over all library sizes,
  dashed line = chance (0.5), star = the split's best setting.
- `accuracy_heatmap.png`: one panel per split; x = sensitivity, y = library size, colour = balanced accuracy
  (blue = better than chance, white = 0.5, red = worse), star = best.
- `far_frr.png`: FAR (orange) and FRR (blue) against sensitivity at each split's best library size; dashed line =
  EER, dotted line = best sensitivity.
- `confusion_best.png`: the 2 × 2 matrix of each split's best setting (rows = rejected / accepted, columns =
  actually impostor / actually legitimate). Each cell shows its count and its share of the column; the shade is
  that share, so a dark TP means most impostors were caught and a dark FP means most real users were blocked.

## Algorithm

```
limit ← one grid step past the last sensitivity where any setting differs from 0.5   (x-axis of the first three)
per split: draw the panels from confusion.csv, mark best.csv's row
```

The x-axis is cut at `limit` because above it every setting is 0.5; the figure titles say so.
