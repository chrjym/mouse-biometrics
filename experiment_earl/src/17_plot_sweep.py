#!/usr/bin/env python3
"""Draw the sweep of 16 (accuracy vs sensitivity per split, sessions x sensitivity heatmaps, FAR/FRR, confusion matrices) -> runs/<hash>/sweep/."""

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


def load_best(folder: Path) -> tuple[dict | None, pd.DataFrame | None]:
    """18's choices if it has run: per split {(legit, impostor): row} and the per-user table; else (None, None)."""
    best = folder / "best"
    if not (best / "best_splits.csv").exists():
        print("No best/ yet: run 18_best_setting.py first to mark the best settings")
        return None, None
    splits = pd.read_csv(best / "best_splits.csv")
    return {(r.n_legitimate, r.n_impostor): r for r in splits.itertuples()}, pd.read_csv(best / "best_users.csv")


def best_text(b) -> str:
    return (f"best: sensitivity {b.sensitivity:g}, {b.sessions} session{'s' if b.sessions > 1 else ''}\n"
            f"BA pick {b.balanced_accuracy_pick:.2f} → check {b.balanced_accuracy_check:.2f}")


def mark_best_line(ax, part: pd.DataFrame, b) -> None:
    """The split's best library size as an orange line, its best sensitivity as a star on it."""
    line = part[part["sessions"] == b.sessions]
    ax.plot(line["sensitivity"], line["balanced_accuracy"], color="#eb6834", lw=1.5, ls=":",
            label="best library size (18)")
    y = line.loc[line["sensitivity"].round(4) == round(b.sensitivity, 4), "balanced_accuracy"].iloc[0]
    ax.scatter([b.sensitivity], [y], marker="*", s=200, color="#eb6834", edgecolor="white", lw=1, zorder=5)
    ax.text(0.97, 0.97, best_text(b), transform=ax.transAxes, ha="right", va="top", fontsize=7,
            bbox=dict(facecolor="white", edgecolor="0.8", boxstyle="round,pad=0.3"))


def plot_accuracy(table: pd.DataFrame, sessions: list[int], path: Path, best: dict | None = None) -> None:
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
        if best and (legit, impostor) in best:
            mark_best_line(ax, part, best[(legit, impostor)])
        ax.set(title=label(legit, impostor), xlabel="sensitivity", xlim=xlim, ylim=(0.5 - reach, 0.5 + reach))
        ax.grid(alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0][0].set_ylabel("balanced accuracy = 1 − (FAR + FRR) / 2")
    axes[0][-1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_heatmaps(table: pd.DataFrame, path: Path, best: dict | None = None, users: pd.DataFrame | None = None) -> None:
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
        if users is not None:
            mine = users[(users.n_legitimate == legit) & (users.n_impostor == impostor)]
            ax.scatter(mine.sensitivity, mine.sessions, s=28, facecolor="none", edgecolor="#1a1a1a", lw=1.2,
                       zorder=3, label="best per user")
            for r in mine.itertuples():
                ax.annotate(r.user, (r.sensitivity, r.sessions), xytext=(4, 3), textcoords="offset points",
                            fontsize=6.5, color="#1a1a1a")
        if best and (legit, impostor) in best:
            b = best[(legit, impostor)]
            ax.scatter([b.sensitivity], [b.sessions], marker="*", s=220, color="#eb6834", edgecolor="white", lw=1,
                       zorder=4, label="best for the split")
            ax.text(0.97, 0.97, best_text(b), transform=ax.transAxes, ha="right", va="top", fontsize=7.5,
                    bbox=dict(facecolor="white", edgecolor="0.8", boxstyle="round,pad=0.3"))
        ax.set_xlabel("sensitivity (higher = more lenient)")
        ax.set_xlim(*active_xlim(table))
    axes[0][0].set_ylabel("sessions in each user's library")
    if best:
        axes[0][0].legend(frameon=True, fontsize=7, loc="lower right")
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


def plot_confusion(table: pd.DataFrame, sessions: int, sensitivities: list[float], path: Path) -> None:
    """Rows = splits, columns = a few sensitivities at one library size: each 2 x 2 matrix shows its counts and each
    cell's share of its column (the shade), so a dark TP = most impostors caught, a dark TN = most real users accepted.
    The columns are fixed sample points, not a chosen best setting."""
    splits = list(table.groupby(SPLIT, sort=False))
    fig, axes = plt.subplots(len(splits), len(sensitivities), figsize=(2.6 * len(sensitivities), 2.5 * len(splits)),
                             squeeze=False, layout="constrained")
    rows, cols = ["rejected", "accepted"], ["actual\nimpostor", "actual\nlegitimate"]
    for r, ((legit, impostor), part) in enumerate(splits):
        for c, sens in enumerate(sensitivities):
            ax = axes[r][c]
            cell = part[(part["sessions"] == sessions) & (part["sensitivity"].round(4) == round(sens, 4))].iloc[0]
            counts = np.array([[cell["TP"], cell["FP"]], [cell["FN"], cell["TN"]]])
            share = counts / counts.sum(axis=0, keepdims=True)
            ax.imshow(share, cmap="Blues", vmin=0, vmax=1)
            for i in range(2):
                for j in range(2):
                    name = [["TP", "FP"], ["FN", "TN"]][i][j]
                    ax.text(j, i, f"{name}\n{counts[i, j]:.0f}\n{share[i, j]:.0%}", ha="center", va="center",
                            fontsize=8, color="white" if share[i, j] > 0.6 else "#1a1a1a")
            ax.set_xticks([0, 1], cols if r == len(splits) - 1 else ["", ""], fontsize=7)
            ax.set_yticks([0, 1], rows if c == 0 else ["", ""], fontsize=7)
            ax.tick_params(length=0)
            ax.spines[:].set_visible(False)
            ba = cell["balanced_accuracy"]
            ax.set_title(f"sensitivity {sens:g}  ·  BA {ba:.2f}", fontsize=8)
            if c == 0:
                ax.set_ylabel(label(legit, impostor), fontsize=8)
    fig.suptitle(f"Confusion matrices at {sessions} sessions per library (positive = impostor; shade = share of "
                 f"the column; BA 0.5 = chance)", fontsize=9)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_simple(table: pd.DataFrame, users: pd.DataFrame, path: Path) -> None:
    """One plain chart: balanced accuracy (%) against sensitivity, one line per split at one shared library size
    (the median of 18's per-user best sizes), the too-strict / just-right / too-loose zones, a star at each peak."""
    k = int(users["sessions"].median())
    fig, ax = plt.subplots(figsize=(8, 4.6), layout="constrained")
    peaks = []
    for colour, ((legit, impostor), part) in zip(COLORS, table.groupby(SPLIT, sort=False)):
        line = part[(part["sessions"] == k) & (part["sensitivity"] <= 0.10)]
        ax.plot(line["sensitivity"], line["balanced_accuracy"] * 100, color=colour, lw=2, label=label(legit, impostor))
        peak = line.loc[line["balanced_accuracy"].idxmax()]
        peaks.append(peak["sensitivity"])
        ax.scatter([peak["sensitivity"]], [peak["balanced_accuracy"] * 100], marker="*", s=180, color=colour,
                   edgecolor="white", lw=1, zorder=5)
    low, high = min(peaks), max(peaks)
    ax.axvspan(0.005, low - 0.005, color="#eb6834", alpha=0.08, lw=0)
    ax.axvspan(low - 0.005, high + 0.005, color="#1baf7a", alpha=0.14, lw=0)
    ax.axvspan(high + 0.005, 0.105, color="0.5", alpha=0.08, lw=0)
    for x, text in (((0.005 + low - 0.005) / 2, "too\nstrict"), ((low + high) / 2, f"just right\n{low:g}–{high:g}"),
                    ((high + 0.105) / 2, "too loose: almost everyone accepted")):
        ax.text(x, 74, text, ha="center", va="top", fontsize=9, color="#1a1a1a")
    ax.axhline(50, color="0.4", lw=1, ls="--")
    ax.text(0.104, 50.5, "50% = guessing", ha="right", va="bottom", fontsize=8, color="0.4")
    ax.set(xlim=(0.005, 0.105), ylim=(45, 75), xlabel="sensitivity (how loosely strokes may match)",
           ylabel="correct decisions (balanced accuracy, %)")
    ax.set_title(f"Best sensitivity: about {low:g}–{high:g}  (★ = peak of each mix, {k} sessions per user)", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, fontsize=8, loc="upper right", bbox_to_anchor=(1, 0.85))
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
    best, users = load_best(folder)
    plot_accuracy(table, sessions, folder / "accuracy_vs_sensitivity.png", best)
    plot_heatmaps(table, folder / "accuracy_heatmap.png", best, users)
    plot_errors(table, sessions, folder / "far_frr.png")
    plot_confusion(table, m, [0.01, 0.02, 0.05, 0.10], folder / "confusion_matrices.png")
    if best:
        plot_simple(table, users, folder / "best_sensitivity.png")
    print(f"{table.groupby(SPLIT).ngroups} splits, {len(table)} confusion matrices plotted")
    print(f"Output: {folder}")


if __name__ == "__main__":
    main()
