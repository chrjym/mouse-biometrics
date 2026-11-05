#!/usr/bin/env python3
"""Plot ranks a-b (e.g. 1-10, 11-20) of runs/best_balanced/best_per_seed.csv (17_best_balanced.py): one row per seed with its best sensitivity, legitimate and impostor sessions through and accuracy, into runs/best_balanced/plots/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
OUT = cfg_mod.RUNS / "best_balanced"
LEGIT, IMPOSTOR, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a64", "#e6e5e0"


def parse_rows(text: str) -> tuple[int, int]:
    """'10' -> (1, 10); '11-20' -> (11, 20)."""
    low, _, high = text.partition("-")
    first, last = (1, int(low)) if not high else (int(low), int(high))
    if first < 1 or last < first:
        raise argparse.ArgumentTypeError(f"rows must be N or A-B with 1 <= A <= B, got {text!r}")
    return first, last


def plot(rows: pd.DataFrame, title: str, path: Path) -> None:
    """Per seed (rank order, top to bottom): legitimate and impostor sessions through as bars, accuracy as a dot."""
    n = len(rows)
    fig, ax = plt.subplots(figsize=(10, 1.2 + 0.55 * n), layout="constrained")
    y = list(range(n))
    h = 0.36
    for offset, column, color, name in ((-h / 2, "legit_through", LEGIT, "legitimate sessions through"),
                                        (h / 2, "impostor_through", IMPOSTOR, "impostor sessions through")):
        values = rows[column].to_numpy()
        bars = ax.barh([i + offset for i in y], values, height=h - 0.04, color=color, label=name, zorder=2)
        for bar, qualifies in zip(bars, rows["legit_ahead"]):
            bar.set_hatch("" if qualifies else "//")
            bar.set_edgecolor("white")
        for i, v in zip(y, values):
            ax.text(v + 0.01, i + offset, f"{v:.2f}", va="center", fontsize=7, color=MUTED)
    ax.scatter(rows["accuracy"], y, s=60, color=INK, edgecolor="white", linewidth=1.5, zorder=3, label="accuracy")
    for i, r in enumerate(rows.itertuples(index=False)):
        ax.text(1.13, i, f"acc {r.accuracy:.3f}   legit {r.TN}/{r.TN + r.FP}, impostor {r.FN}/{r.FN + r.TP}",
                va="center", fontsize=7.5, color=INK)
    labels = [f"#{r.rank}  seed {r.seed}  sensitivity {r.sensitivity:g}" + ("" if r.legit_ahead else "  (legitimate rule not met)")
              for r in rows.itertuples(index=False)]
    ax.set_yticks(y, labels, fontsize=8, color=INK)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.axvline(0.5, color=MUTED, linewidth=0.8, linestyle=":", zorder=1)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("share of sessions (accuracy = (impostors rejected + legitimate accepted) / all)", fontsize=8,
                  color=MUTED)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=8)
    ax.set_title(title, fontsize=10, color=INK, pad=28)
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=parse_rows, default=(1, 10),
                        help="ranks to plot: N = top N, A-B = ranks A to B, e.g. 10, 11-20 (default 1-10)")
    args = parser.parse_args()
    first, last = args.rows
    source = OUT / "best_per_seed.csv"
    if not source.exists():
        raise SystemExit(f"No {source}: run 17_best_balanced.py first")
    table = pd.read_csv(source)
    rows = table[(table["rank"] >= first) & (table["rank"] <= last)]
    if rows.empty:
        raise SystemExit(f"Ranks {first}-{last} are past the end: {len(table)} seeds")
    end = int(rows["rank"].max())

    (OUT / "plots").mkdir(parents=True, exist_ok=True)
    path = OUT / "plots" / f"best_per_seed_rank_{first}-{end}.png"
    title = (f"Best sensitivity per seed (experiment 1, all splits added), ranks {first}-{end} of {len(table)} seeds\n"
             f"ranked by accuracy, highest first; hatched = legitimate rule not met: more legitimate than impostor sessions through "
             f"and legitimate >= 0.5")
    plot(rows, title, path)
    print(f"Plotted ranks {first}-{end} of {len(table)} seeds -> {path}")


if __name__ == "__main__":
    main()
