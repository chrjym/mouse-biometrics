# `14_plot_sweep.py`: figures of the sensitivity sweep

[← index](README.md) · previous: [13](13_sweep_sensitivity.md)

## What it does

Reads `runs/<hash>/sweep/confusion.csv` (written by [13](13_sweep_sensitivity.md)) and draws four figures into the
same folder. Run 13 → 14.

- `accuracy_vs_sensitivity.png`: one panel per split; balanced accuracy against sensitivity, one line per library
  size of 1, m/4, m/2 and m sessions (m = `sweep_sessions_max`), dashed line = chance (0.5).
- `accuracy_heatmap.png`: one panel per split; x = sensitivity, y = library size, colour = balanced accuracy
  (blue = better than chance, white = 0.5, red = worse).
- `far_frr.png`: FAR and FRR against sensitivity at the same library sizes.
- `confusion_matrices.png`: rows = splits, columns = sensitivity 0.01, 0.02, 0.05, 0.10 at the largest library
  (m sessions). Each 2 × 2 matrix (positive = impostor; rows = rejected / accepted, columns = actual impostor /
  legitimate) shows its counts and each cell's share of its column, which is also the shade. The columns are fixed
  sample points, not a chosen best: they show the move from rejecting everyone (0.01) to accepting everyone (≥ 0.05).
