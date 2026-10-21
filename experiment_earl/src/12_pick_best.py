#!/usr/bin/env python3
"""Pick the best sensitivity and sessions per split (user-level accuracy, session-level tie-break) from runs/<hash>/accuracy.csv (script 10) into runs/<hash>/best/."""

import argparse
import shutil
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
CELL = ["n_legitimate", "n_impostor", "sensitivity", "sessions"]
SPLIT = ["n_legitimate", "n_impostor"]


def score_cells(table: pd.DataFrame) -> pd.DataFrame:
    """Per (split, sensitivity, sessions), both as (legitimate accepted + impostors rejected) / 2, 0.5 = chance:
    user_accuracy over users through (the group's 2026-10-14 rule), session_accuracy over sessions passed."""
    sums = table.groupby(CELL + ["kind"]).agg(passed=("passed", "sum"), tested=("tested", "sum"),
                                              through=("through", "sum"), users=("user", "size")).unstack("kind")
    cells = pd.DataFrame({
        "legit_accepted": sums["passed"]["legitimate"] / sums["tested"]["legitimate"],
        "impostor_accepted": sums["passed"]["impostor"] / sums["tested"]["impostor"],
        "legit_through": sums["through"]["legitimate"], "legit_users": sums["users"]["legitimate"],
        "impostor_through": sums["through"]["impostor"], "impostor_users": sums["users"]["impostor"],
    })
    cells["user_accuracy"] = (cells["legit_through"] / cells["legit_users"]
                              + 1 - cells["impostor_through"] / cells["impostor_users"]) / 2
    cells["session_accuracy"] = (cells["legit_accepted"] + 1 - cells["impostor_accepted"]) / 2
    return cells.reset_index()


def pick_best(cells: pd.DataFrame) -> pd.DataFrame:
    """Highest user accuracy per split; ties go to the higher session accuracy, then fewer sessions, then the
    lower sensitivity."""
    ranked = cells.sort_values(SPLIT + ["user_accuracy", "session_accuracy", "sessions", "sensitivity"],
                               ascending=[True, True, False, False, True, True])
    best = ranked.groupby(SPLIT, as_index=False).head(1).reset_index(drop=True)
    best["beats_chance"] = best["user_accuracy"] > 0.5
    return best


def plot(cells: pd.DataFrame, best: pd.DataFrame, path: Path, title: str) -> None:
    """One heatmap per split: sensitivity x sessions, colour = user accuracy around chance, best cell boxed.
    Sensitivities above the last one where any cell differs from chance are left out (all 0.5 there)."""
    off = cells.loc[((cells["user_accuracy"] - 0.5).abs() > 1e-9) | ((cells["session_accuracy"] - 0.5).abs() > 1e-9),
                    "sensitivity"]
    shown = sorted(cells["sensitivity"].unique())
    top = shown.index(off.max()) + 2 if len(off) else len(shown)
    hidden = shown[top:]
    cells = cells[cells["sensitivity"].isin(shown[:top])]
    splits = list(best[SPLIT].itertuples(index=False, name=None))
    cols = 3
    rows = -(-len(splits) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 3.6 * rows), squeeze=False, sharex=True, sharey=True,
                             layout="constrained")
    norm = TwoSlopeNorm(vmin=0, vcenter=0.5, vmax=1)
    for ax, (legit, impostor) in zip(axes.flat, splits):
        grid = (cells[(cells.n_legitimate == legit) & (cells.n_impostor == impostor)]
                .pivot(index="sensitivity", columns="sessions", values="user_accuracy"))
        image = ax.imshow(grid.values, cmap="RdBu", norm=norm, aspect="auto", origin="lower")
        row = best[(best.n_legitimate == legit) & (best.n_impostor == impostor)].iloc[0]
        x, y = list(grid.columns).index(row.sessions), list(grid.index).index(row.sensitivity)
        ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, edgecolor="black", linewidth=2))
        verdict = "" if row.beats_chance else ", = chance"
        ax.set_title(f"{legit} legit vs {impostor} impostors\nbest {row.user_accuracy:.2f} (sessions "
                     f"{row.session_accuracy:.2f}) at {row.sensitivity:g} / {row.sessions:g} sessions{verdict}",
                     fontsize=9)
        ax.set_xticks(range(len(grid.columns)), [f"{c:g}" for c in grid.columns], fontsize=7)
        ax.set_yticks(range(len(grid.index)), [f"{s:g}" for s in grid.index], fontsize=7)
    for ax in axes.flat[len(splits):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("sessions per user")
    for ax in axes[:, 0]:
        ax.set_ylabel("sensitivity")
    fig.colorbar(image, ax=axes, shrink=0.6, label="user accuracy (0.5 = chance, white)")
    if hidden:
        title += f"\nsensitivities {hidden[0]:g}–{hidden[-1]:g} not shown: every cell there is 0.5"
    fig.suptitle(title, fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ holding accuracy.csv "
                                                "(default: the one config.yaml selects)")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    source = group / "accuracy.csv"
    if not source.exists():
        raise SystemExit(f"No {source}: run 10_plot_accuracy.py {group.name} first")

    table = pd.read_csv(source)
    cells = score_cells(table)
    best = pick_best(cells)
    out = group / "best"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    cells.to_csv(out / "scores.csv", index=False)
    best.to_csv(out / "best.csv", index=False)
    keys = best[CELL].merge(table, on=CELL)
    keys.to_csv(out / "best_rows.csv", index=False)
    for row in best.itertuples():
        figure = group / f"accuracy_{row.n_legitimate}_{row.n_impostor}_sensitivity_{row.sensitivity:g}.png"
        if figure.exists():
            shutil.copy2(figure, out / figure.name)
    plot(cells, best, out / "best_heatmaps.png",
         f"runs/{group.name}: user accuracy = (legitimate users through + impostor users rejected) / 2\n"
         f"box = best per split (ties: session accuracy, then fewer sessions, then lower sensitivity)")

    columns = SPLIT + ["sensitivity", "sessions", "legit_through", "legit_users", "impostor_through",
                       "impostor_users", "user_accuracy", "session_accuracy", "beats_chance"]
    print(best[columns].round(3).to_string(index=False))
    print(f"Cells: {len(cells)}  Splits: {len(best)}  Better than chance: {int(best.beats_chance.sum())}")
    print(f"Output: {out}/ (best.csv, scores.csv, best_rows.csv, best_heatmaps.png, best accuracy figures)")


if __name__ == "__main__":
    main()
