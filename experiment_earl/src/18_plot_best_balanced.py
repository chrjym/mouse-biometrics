#!/usr/bin/env python3
"""Plot ranks a-b (e.g. 1-10, 11-20) of 17_best_balanced.py's ranking over all seeds (or one --seed) for one experiment and split into runs/best_balanced/plots/: legitimate and impostor sessions through and accuracy per setting."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
X = {"exp1": "sensitivity", "exp2": "sessions"}
LEGIT, IMPOSTOR, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1f1f1e", "#6b6a64", "#e6e5e0"


def parse_rows(text: str) -> tuple[int, int]:
    """'10' -> (1, 10); '11-20' -> (11, 20)."""
    low, _, high = text.partition("-")
    first, last = (1, int(low)) if not high else (int(low), int(high))
    if first < 1 or last < first:
        raise argparse.ArgumentTypeError(f"rows must be N or A-B with 1 <= A <= B, got {text!r}")
    return first, last


OUT = cfg_mod.RUNS / "best_balanced"


def read(name: str) -> pd.DataFrame:
    path = OUT / name
    if not path.exists():
        raise SystemExit(f"No {path}: run 17_best_balanced.py first")
    return pd.read_csv(path)


def seed_rows(seed: int, exp: str, split: str) -> pd.DataFrame:
    """One seed's ranking (rank column of 17's scores.csv) for one split."""
    table = read("scores.csv")
    table = table[(table["seed"] == seed) & (table["experiment"] == exp) & (table["split"] == split)]
    table = table.sort_values("rank")
    table["note"] = [f"legit {tn}/{tn + fp}, impostor {fn}/{fn + tp}"
                     for tp, fp, fn, tn in table[["TP", "FP", "FN", "TN"]].itertuples(index=False)]
    return table


def summary_rows(exp: str, split: str) -> pd.DataFrame:
    """The ranking over all seeds (17's summary.csv: times_best, seeds_qualifying, accuracy, x) for one split;
    qualifies = qualifies in at least one seed."""
    table = read("summary.csv")
    table = table[(table["experiment"] == exp) & (table["split"] == split)].sort_values("rank")
    table["note"] = [f"best in {b}/{s} seeds, qualifies in {q}"
                     for b, s, q in table[["times_best", "seeds", "seeds_qualifying"]].itertuples(index=False)]
    return table


def label(row: pd.Series, exp: str) -> str:
    if exp == "exp1":
        setting = f"sensitivity {row['sensitivity']:g}"
    else:
        setting = f"{row['sessions']:g} sessions"
        if "sensitivity" in row and pd.notna(row.get("sensitivity")):
            setting += f" @ {row['sensitivity']:g}"
    return f"#{row['rank']}  {setting}" + ("" if row["qualifies"] else "  (not qualifying)")


def plot(rows: pd.DataFrame, exp: str, title: str, path: Path) -> None:
    """Per ranked setting (top to bottom): legitimate through and impostor through as bars, accuracy as a dot."""
    n = len(rows)
    fig, ax = plt.subplots(figsize=(10, 1.2 + 0.55 * n), layout="constrained")
    y = range(n)
    h = 0.36
    for offset, column, color, name in ((-h / 2, "legit_through", LEGIT, "legitimate sessions through"),
                                        (h / 2, "impostor_through", IMPOSTOR, "impostor sessions through")):
        values = rows[column].to_numpy()
        hatch = ["" if q else "//" for q in rows["qualifies"]]
        bars = ax.barh([i + offset for i in y], values, height=h - 0.04, color=color, label=name, zorder=2)
        for bar, pattern in zip(bars, hatch):
            bar.set_hatch(pattern)
            bar.set_edgecolor("white")
        for i, v in zip(y, values):
            ax.text(v + 0.01, i + offset, f"{v:.2f}", va="center", fontsize=7, color=MUTED)
    ax.scatter(rows["accuracy"], list(y), s=60, color=INK, edgecolor="white", linewidth=1.5, zorder=3,
               label="accuracy")
    for i, (acc, note) in enumerate(rows[["accuracy", "note"]].itertuples(index=False)):
        ax.text(1.13, i, f"acc {acc:.3f}   {note}", va="center", fontsize=7.5, color=INK)
    ax.set_yticks(list(y), [label(r, exp) for _, r in rows.iterrows()], fontsize=8, color=INK)
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
    parser.add_argument("--seed", type=int, help="plot one seed's ranking instead of the ranking over all seeds")
    parser.add_argument("--rows", type=parse_rows, default=(1, 10),
                        help="ranks to plot: N = top N, A-B = ranks A to B, e.g. 10, 11-20 (default 1-10)")
    parser.add_argument("--experiment", choices=list(X), default="exp1", help="exp1 (sensitivity) or exp2 (sessions)")
    parser.add_argument("--split", default="all", help="'all' (every split added) or e.g. '1 x 5' (default all)")
    parser.add_argument("--qualifying-only", action="store_true",
                        help="rank only the qualifying settings (ranks renumbered 1, 2, ... among them)")
    args = parser.parse_args()
    first, last = args.rows

    if args.seed is None:
        table = summary_rows(args.experiment, args.split)
        source = f"over {int(table['seeds'].max()) if len(table) else 0} seeds"
    else:
        table = seed_rows(args.seed, args.experiment, args.split)
        source = f"seed {args.seed}" + (f", runs/{table['hash'].iloc[0]}" if len(table) else "")
    out_dir = OUT / "plots"
    name = "all_seeds" if args.seed is None else f"seed_{args.seed}"
    if args.qualifying_only:
        table = table[table["qualifies"]].assign(rank=lambda t: range(1, len(t) + 1))
    if table.empty:
        raise SystemExit(f"No {'qualifying ' if args.qualifying_only else ''}rows for {args.experiment} "
                         f"split {args.split!r}")
    rows = table[(table["rank"] >= first) & (table["rank"] <= last)]
    if rows.empty:
        raise SystemExit(f"Ranks {first}-{last} are past the end: {len(table)} ranked rows")

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_qualifying" if args.qualifying_only else ""
    path = out_dir / f"{name}_{args.experiment}_{args.split.replace(' ', '')}{suffix}_rank_{first}-{rows['rank'].max()}.png"
    title = (f"{'Experiment 1: sensitivity' if args.experiment == 'exp1' else 'Experiment 2: sessions'}, "
             f"split {args.split}, ranks {first}-{rows['rank'].max()} of {len(table)}"
             f"{' qualifying' if args.qualifying_only else ''} ({source})\n"
             + ("rank: seeds where it is the best qualifying setting, then seeds where it qualifies, then mean accuracy; "
                "bars and dot = means over seeds; hatched = qualifies in no seed"
                if args.seed is None else
                "rank: qualifying first (more legitimate than impostor sessions through, legitimate >= min), "
                "then accuracy; hatched = not qualifying"))
    plot(rows, args.experiment, title, path)
    print(f"Plotted ranks {first}-{rows['rank'].max()} of {len(table)} -> {path}")


if __name__ == "__main__":
    main()
