#!/usr/bin/env python3
"""Draw the sweep of 16 (accuracy vs sensitivity per split, sessions x sensitivity heatmaps, FAR/FRR) -> runs/<hash>/sweep/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

cfg_mod = import_module("00_config")
sweep_mod = import_module("16_sweep_sensitivity")

ROOT = Path(__file__).resolve().parents[1]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # fixed order, one per split
SPLIT = ["n_legitimate", "n_impostor"]


def label(legit: int, impostor: int) -> str:
    return f"{legit} legitimate vs {impostor} impostor{'s' if impostor > 1 else ''}"


def active_xlim(table: pd.DataFrame) -> tuple[float, float]:
    """Sensitivity range where FAR and FRR are both above 0 (outside it every cell is 0.5), padded a little."""
    active = table[(table["FAR"] > 0) & (table["FRR"] > 0)]["sensitivity"]
    low, high = table["sensitivity"].min(), table["sensitivity"].max()
    pad = (high - low) / 20
    return (max(active.min() - pad, low), min(active.max() + pad, high)) if len(active) else (low, high)


def plot_accuracy(table: pd.DataFrame, sessions: list[int], path: Path) -> None:
    """One panel per split: balanced accuracy (y) against sensitivity (x), one line per session count (light = few,
    dark = many), grey band = range over every session count. x is cut to where anything changes."""
    xlim = active_xlim(table)
    reach = max(abs(table["balanced_accuracy"] - 0.5).max() + 0.02, 0.25)
    shades = plt.get_cmap("Blues")([0.35 + 0.65 * i / max(len(sessions) - 1, 1) for i in range(len(sessions))])
    splits = list(table.groupby(SPLIT, sort=False))
    fig, axes = plt.subplots(1, len(splits), figsize=(4.2 * len(splits), 3.8), sharey=True, squeeze=False,
                             layout="constrained")
    for ax, ((legit, impostor), part) in zip(axes[0], splits):
        spread = part.groupby("sensitivity")["balanced_accuracy"].agg(["min", "max"])
        ax.fill_between(spread.index, spread["min"], spread["max"], color="0.85", lw=0, label="all session counts")
        for shade, k in zip(shades, sessions):
            line = part[part["sessions"] == k]
            ax.plot(line["sensitivity"], line["balanced_accuracy"], color=shade, lw=2, label=f"{k} sessions")
        ax.axhline(0.5, color="0.4", lw=1, ls="--")
        ax.text(xlim[1], 0.5, "chance ", ha="right", va="bottom", fontsize=8, color="0.4")
        ax.set(title=label(legit, impostor), xlabel="sensitivity", xlim=xlim, ylim=(0.5 - reach, 0.5 + reach))
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("balanced accuracy = 1 − (FAR + FRR) / 2")
    axes[0][-1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_heatmaps(table: pd.DataFrame, path: Path) -> None:
    """Sessions (y) x sensitivity (x), one panel per split. Each cell is one setting; colour = balanced accuracy
    (RdBu around chance as 12, scale cut to 0.5 +- the largest gap so weak effects still show)."""
    splits = list(table.groupby(SPLIT, sort=False))
    reach = max(abs(table["balanced_accuracy"] - 0.5).max(), 0.05)
    norm = TwoSlopeNorm(vmin=0.5 - reach, vcenter=0.5, vmax=0.5 + reach)
    sens = sorted(table["sensitivity"].unique())
    half = (sens[1] - sens[0]) / 2 if len(sens) > 1 else 0.005
    fig, axes = plt.subplots(1, len(splits), figsize=(4.4 * len(splits), 4.4), sharey=True, squeeze=False,
                             layout="constrained")
    for ax, ((legit, impostor), part) in zip(axes[0], splits):
        grid = part.pivot(index="sessions", columns="sensitivity", values="balanced_accuracy")
        image = ax.imshow(grid, aspect="auto", origin="lower", cmap="RdBu", norm=norm, interpolation="nearest",
                          extent=(grid.columns.min() - half, grid.columns.max() + half,
                                  grid.index.min() - 0.5, grid.index.max() + 0.5))
        ax.set_title(label(legit, impostor), fontsize=10)
        ax.set_xlabel("sensitivity (higher = more lenient)")
        ax.set_xlim(*active_xlim(table))
    axes[0][0].set_ylabel("sessions in each user's library")
    bar = fig.colorbar(image, ax=axes[0].tolist(), shrink=0.85)
    bar.set_ticks([0.5 - reach, 0.5, 0.5 + reach])
    bar.set_ticklabels([f"{0.5 - reach:.2f}\nworse than\nchance", "0.50 chance", f"{0.5 + reach:.2f}\nbetter than\nchance"])
    bar.set_label("balanced accuracy")
    fig.suptitle("Each cell = one setting (sensitivity × library size). Blue = tells impostors from real users better "
                 "than guessing, red = worse, white = no better than guessing.", fontsize=9)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_errors(table: pd.DataFrame, sessions: list[int], path: Path) -> None:
    """FAR and FRR against sensitivity at a few session counts (light = few, dark = many); where they cross is the EER."""
    shade = lambda cmap: plt.get_cmap(cmap)([0.35 + 0.65 * i / max(len(sessions) - 1, 1) for i in range(len(sessions))])
    far, frr = shade("Oranges"), shade("Blues")
    splits = list(table.groupby(SPLIT, sort=False))
    fig, axes = plt.subplots(1, len(splits), figsize=(4.5 * len(splits), 4), sharey=True, squeeze=False)
    for ax, ((legit, impostor), part) in zip(axes[0], splits):
        for i, k in enumerate(sessions):
            line = part[part["sessions"] == k]
            ax.plot(line["sensitivity"], line["FAR"], color=far[i], lw=2, label=f"FAR, {k} sessions")
            ax.plot(line["sensitivity"], line["FRR"], color=frr[i], lw=2, label=f"FRR, {k} sessions")
        ax.set(title=label(legit, impostor), xlabel="sensitivity", xlim=active_xlim(table), ylim=(0, 1))
        ax.grid(alpha=0.25)
    axes[0][0].set_ylabel("error rate (FAR = impostors let in, FRR = legitimate rejected)")
    axes[0][-1].legend(frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    plan, base = sweep_mod.load_plan(), cfg_mod.load_config()
    folder = sweep_mod.out_folder(plan, base)
    table = pd.read_csv(folder / "confusion.csv")
    m = plan["max_sessions"]
    sessions = sorted({1, max(m // 4, 1), max(m // 2, 1), m})
    plot_accuracy(table, sessions, folder / "accuracy_vs_sensitivity.png")
    plot_heatmaps(table, folder / "accuracy_heatmap.png")
    plot_errors(table, sessions, folder / "far_frr.png")
    print(f"{table.groupby(SPLIT).ngroups} splits, {len(table)} confusion matrices plotted")
    print(f"Output: {folder}")


if __name__ == "__main__":
    main()
