#!/usr/bin/env python3
"""Best sensitivity and library size per legitimate user and per split, chosen on the pick half of 16's test sessions and scored on the check half -> runs/<hash>/sweep/best/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cfg_mod = import_module("00_config")
sweep_mod = import_module("16_sweep_sensitivity")

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ["n_legitimate", "n_impostor"]
SETTING = ["sessions", "sensitivity"]
COUNTS = ["TP", "FP", "FN", "TN"]


def scores(table: pd.DataFrame) -> pd.DataFrame:
    table = table.copy()
    table["FAR"] = table["FN"] / (table["TP"] + table["FN"])
    table["FRR"] = table["FP"] / (table["FP"] + table["TN"])
    table["balanced_accuracy"] = 1 - (table["FAR"] + table["FRR"]) / 2
    return table


def pick(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Per group: the setting with the highest pick-half balanced accuracy; ties go to fewer sessions (less data asked
    of the user), then the lower sensitivity. Its check-half scores are attached unchanged."""
    halves = {h: part.drop(columns="half") for h, part in table.groupby("half")}
    ranked = halves["pick"].assign(score=halves["pick"]["balanced_accuracy"].round(9)).sort_values(
        keys + ["score", "sessions", "sensitivity"], ascending=[True] * len(keys) + [False, True, True])
    best = ranked.groupby(keys, sort=False).head(1).drop(columns="score")
    check = halves["check"][keys + SETTING + COUNTS + ["FAR", "FRR", "balanced_accuracy"]]
    return best.merge(check, on=keys + SETTING, suffixes=("_pick", "_check")).reset_index(drop=True)


def user_label(row) -> str:
    return f"{row.user} ({row.n_legitimate}L×{row.n_impostor}I)"


def plot_best(users: pd.DataFrame, path: Path) -> None:
    """One row per legitimate user: balanced accuracy on the pick half (hollow) and the check half (filled)."""
    users = users.sort_values("balanced_accuracy_check").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.5, 0.42 * len(users) + 1.4), layout="constrained")
    for i, row in users.iterrows():
        ax.plot([row.balanced_accuracy_pick, row.balanced_accuracy_check], [i, i], color="0.8", lw=2, zorder=1)
    ax.scatter(users["balanced_accuracy_pick"], users.index, s=60, facecolor="white", edgecolor="#2a78d6", lw=2,
               zorder=2, label="pick half (chosen here)")
    ax.scatter(users["balanced_accuracy_check"], users.index, s=60, color="#2a78d6", zorder=3,
               label="check half (unseen sessions)")
    ax.axvline(0.5, color="0.4", lw=1, ls="--")
    ax.set_yticks(users.index, [f"{user_label(r)}  s={r.sensitivity:g}, {r.sessions} sess." for r in users.itertuples()],
                  fontsize=8)
    ax.set(xlabel="balanced accuracy (0.5 = chance)", xlim=(0.3, 1.0))
    ax.grid(axis="x", alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("Best setting per legitimate user: chosen on one half, checked on the other", fontsize=10)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    plan, base = sweep_mod.load_plan(), cfg_mod.load_config()
    folder = sweep_mod.out_folder(plan, base)
    path = folder / "user_confusion.csv"
    if not path.exists():
        raise SystemExit(f"{path} is missing; run 16_sweep_sensitivity.py (delete sweep/parts/ if it ran before 18 existed)")
    table = pd.read_csv(path)
    users = pick(table, SPLIT + ["user"])
    splits = pick(scores(table.groupby(SPLIT + ["half"] + SETTING, as_index=False)[COUNTS].sum()), SPLIT)

    out = folder / "best"
    out.mkdir(exist_ok=True)
    users.to_csv(out / "best_users.csv", index=False)
    splits.to_csv(out / "best_splits.csv", index=False)
    plot_best(users, out / "best_users.png")

    columns = ["sensitivity", "sessions", "balanced_accuracy_pick", "balanced_accuracy_check", "FAR_check", "FRR_check"]
    print("Per legitimate user:")
    print(users[SPLIT + ["user"] + columns].round(3).to_string(index=False))
    print("\nPer split:")
    print(splits[SPLIT + columns].round(3).to_string(index=False))
    print(f"Output: {out}/ (best_users.csv, best_splits.csv, best_users.png)")


if __name__ == "__main__":
    main()
