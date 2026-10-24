#!/usr/bin/env python3
"""Draw the sweep of 16 (runs/<hash>/sweep/): balanced accuracy against sensitivity, its heatmap, FAR/FRR and the best confusion matrices."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

cfg_mod = import_module("00_config")

LINE_SESSIONS = (1, 10, 20, 40)                       # library sizes drawn as lines
LINE_COLOURS = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")  # one blue ramp, light = small library
FAR_COLOUR, FRR_COLOUR = "#eb6834", "#2a78d6"
MUTED = "#52514e"


def split_label(legit: int, impostor: int) -> str:
    return f"{legit} legitimate vs {impostor} impostor{'s' if impostor > 1 else ''}"


def panels(n: int, width: float, height: float, **kwargs):
    cols = min(n, 2)
    rows = -(-n // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(width * cols, height * rows), squeeze=False,
                             layout="constrained", **kwargs)
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    return fig, axes.flat[:n]


def zoom_limit(table: pd.DataFrame) -> float:
    """The sensitivity one grid step past the last one where any setting differs from chance."""
    grid = np.sort(table.sensitivity.unique())
    off = table.loc[(table.balanced_accuracy - 0.5).abs() > 1e-9, "sensitivity"]
    if not len(off):
        return float(grid[-1])
    return float(grid[min(np.searchsorted(grid, off.max()) + 1, len(grid) - 1)])


def by_split(table: pd.DataFrame, best: pd.DataFrame):
    for row in best.itertuples():
        yield row, table[(table.n_legitimate == row.n_legitimate) & (table.n_impostor == row.n_impostor)]


def plot_accuracy(table: pd.DataFrame, best: pd.DataFrame, limit: float, path: Path) -> None:
    fig, axes = panels(len(best), 6, 3.8, sharey=True)
    for ax, (row, part) in zip(axes, by_split(table, best)):
        part = part[part.sensitivity <= limit]
        band = part.groupby("sensitivity").balanced_accuracy.agg(["min", "max"])
        ax.fill_between(band.index, band["min"], band["max"], color="#d9d8d3", linewidth=0,
                        label="range over all library sizes")
        ax.axhline(0.5, color=MUTED, linewidth=1, linestyle="--")
        for k, colour in zip(LINE_SESSIONS, LINE_COLOURS):
            line = part[part.sessions == k]
            if len(line):
                ax.plot(line.sensitivity, line.balanced_accuracy, color=colour, linewidth=2,
                        label=f"{k} session{'s' if k > 1 else ''}")
        ax.plot(row.sensitivity, row.balanced_accuracy, marker="*", markersize=14, color="black", linestyle="none",
                label="best setting")
        ax.annotate(f"{row.balanced_accuracy:.2f} at {row.sensitivity:g}, {row.sessions} sessions",
                    (row.sensitivity, row.balanced_accuracy), xytext=(8, 6), textcoords="offset points", fontsize=8)
        ax.set_title(split_label(row.n_legitimate, row.n_impostor), fontsize=10)
        ax.set_xlabel("sensitivity")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("balanced accuracy (0.5 = chance)")
    if len(axes) > 2:
        axes[2].set_ylabel("balanced accuracy (0.5 = chance)")
    axes[0].legend(fontsize=7, title="library", title_fontsize=7, loc="lower right")
    fig.suptitle(f"Balanced accuracy against sensitivity (shown up to {limit:g}; above it every setting is 0.5)",
                 fontsize=11)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_heatmap(table: pd.DataFrame, best: pd.DataFrame, limit: float, path: Path) -> None:
    fig, axes = panels(len(best), 6, 4.2, sharey=True)
    norm = TwoSlopeNorm(vmin=0, vcenter=0.5, vmax=1)
    for ax, (row, part) in zip(axes, by_split(table, best)):
        grid = part[part.sensitivity <= limit].pivot(index="sessions", columns="sensitivity",
                                                     values="balanced_accuracy")
        step = grid.columns[1] - grid.columns[0] if len(grid.columns) > 1 else 0.01
        extent = (grid.columns[0] - step / 2, grid.columns[-1] + step / 2, grid.index[0] - 0.5, grid.index[-1] + 0.5)
        image = ax.imshow(grid.values, cmap="RdBu", norm=norm, aspect="auto", origin="lower", extent=extent,
                          interpolation="nearest")
        ax.plot(row.sensitivity, row.sessions, marker="*", markersize=12, color="black", linestyle="none")
        ax.set_title(f"{split_label(row.n_legitimate, row.n_impostor)}\nbest {row.balanced_accuracy:.2f} at "
                     f"{row.sensitivity:g}, {row.sessions} sessions", fontsize=10)
        ax.set_xlabel("sensitivity")
    axes[0].set_ylabel("library size (sessions)")
    if len(axes) > 2:
        axes[2].set_ylabel("library size (sessions)")
    fig.colorbar(image, ax=list(axes), shrink=0.7,
                 label="balanced accuracy (blue = better than chance, white = 0.5, red = worse)")
    fig.suptitle(f"Every setting of the sweep (sensitivity shown up to {limit:g}); star = best per split", fontsize=11)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_far_frr(table: pd.DataFrame, best: pd.DataFrame, limit: float, path: Path) -> None:
    fig, axes = panels(len(best), 6, 3.8, sharey=True)
    for ax, (row, part) in zip(axes, by_split(table, best)):
        line = part[(part.sessions == row.sessions) & (part.sensitivity <= limit)]
        ax.plot(line.sensitivity, line.far, color=FAR_COLOUR, linewidth=2, label="FAR: impostors let in")
        ax.plot(line.sensitivity, line.frr, color=FRR_COLOUR, linewidth=2, label="FRR: real users blocked")
        ax.axhline(row.eer, color=MUTED, linewidth=1, linestyle="--")
        ax.text(line.sensitivity.iloc[-1], row.eer, f"EER {row.eer:.2f}", ha="right", va="bottom", fontsize=8,
                color=MUTED)
        ax.axvline(row.sensitivity, color="black", linewidth=1, linestyle=":")
        ax.set_title(f"{split_label(row.n_legitimate, row.n_impostor)}, {row.sessions}-session library\n"
                     f"best sensitivity {row.sensitivity:g}: FAR {row.far:.2f}, FRR {row.frr:.2f}", fontsize=10)
        ax.set_xlabel("sensitivity")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("share of test sessions")
    if len(axes) > 2:
        axes[2].set_ylabel("share of test sessions")
    axes[0].legend(fontsize=8, loc="center right", bbox_to_anchor=(1, 0.75))
    fig.suptitle("FAR and FRR at each split's best library size (dotted = best sensitivity)", fontsize=11)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_confusion(best: pd.DataFrame, path: Path) -> None:
    """Rows = decision, columns = truth (positive = impostor). Shade = the cell's share of its column, so the
    shade is the rate (TP and FN share the impostor column, FP and TN the legitimate one)."""
    fig, axes = panels(len(best), 4.6, 3.8)
    for ax, row in zip(axes, best.itertuples()):
        counts = np.array([[row.tp, row.fp], [row.fn, row.tn]])
        names = np.array([["TP", "FP"], ["FN", "TN"]])
        share = counts / counts.sum(axis=0, keepdims=True)
        ax.imshow(share, cmap="Blues", vmin=0, vmax=1)
        for (r, c), n in np.ndenumerate(counts):
            ax.text(c, r, f"{names[r, c]}\n{n} ({share[r, c]:.0%})", ha="center", va="center", fontsize=10,
                    color="white" if share[r, c] > 0.6 else "black")
        ax.set_xticks([0, 1], ["actually\nimpostor", "actually\nlegitimate"])
        ax.set_yticks([0, 1], ["rejected", "accepted"])
        ax.set_title(f"{split_label(row.n_legitimate, row.n_impostor)}\n{row.sensitivity:g}, {row.sessions} sessions: "
                     f"balanced accuracy {row.balanced_accuracy:.2f}", fontsize=9)
    fig.suptitle("Confusion matrix at each split's best setting (shade = share of the column)", fontsize=11)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ holding sweep/ (default: the one config.yaml selects)")
    args = parser.parse_args()
    folder = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0]) / "sweep"
    if not (folder / "confusion.csv").exists():
        raise SystemExit(f"No {folder / 'confusion.csv'}: run 16_sweep_sensitivity.py first")
    table, best = pd.read_csv(folder / "confusion.csv"), pd.read_csv(folder / "best.csv")
    limit = zoom_limit(table)
    plot_accuracy(table, best, limit, folder / "accuracy_vs_sensitivity.png")
    plot_heatmap(table, best, limit, folder / "accuracy_heatmap.png")
    plot_far_frr(table, best, limit, folder / "far_frr.png")
    plot_confusion(best, folder / "confusion_best.png")
    print(f"Splits: {len(best)}  Sensitivity shown up to {limit:g}")
    print(f"Output: {folder}/ (accuracy_vs_sensitivity.png, accuracy_heatmap.png, far_frr.png, confusion_best.png)")


if __name__ == "__main__":
    main()
