# `17_plot_sweep.py`: figures of the sensitivity sweep

[← index](README.md) · previous: [16](16_sweep_sensitivity.md)

## What it does

Reads `runs/<hash>/sweep/confusion.csv` (written by [16](16_sweep_sensitivity.md)) and draws three figures into the
same folder. No best setting is marked: see 16 for why.

- `accuracy_vs_sensitivity.png`: one panel per split; balanced accuracy against sensitivity, one line per library
  size of 1, m/4, m/2 and m sessions (m = `sweep_sessions_max`), dashed line = chance (0.5).
- `accuracy_heatmap.png`: one panel per split; x = sensitivity, y = library size, colour = balanced accuracy
  (blue = better than chance, white = 0.5, red = worse).
- `far_frr.png`: FAR and FRR against sensitivity at the same library sizes.
