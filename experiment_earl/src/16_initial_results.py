#!/usr/bin/env python3
"""Draw the initial results from runs/<hash>/accuracy.csv (script 10): experiment 1 (user x user x sensitivity, 1 session) and experiment 2 (user x session x sensitivity) -> runs/<hash>/initial_results/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
CELL = ["n_legitimate", "n_impostor", "sensitivity", "sessions"]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#5a48d6"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X"]
BACKGROUND = "#fcfcfa"
METRICS = [("legitimate_accuracy", "Legitimate accuracy", "own held-out sessions accepted"),
           ("impostor_accuracy", "Impostor accuracy", "impostor users rejected"),
           ("accuracy", "Accuracy", "mean of the two; 0.5 = chance")]
ROW_LABELS = ["legitimate accuracy", "impostor accuracy", "mean; 0.5 = chance"]


def score_cells(table: pd.DataFrame) -> pd.DataFrame:
    """Per (split, sensitivity, sessions): users through and sessions passed for each kind, and the accuracies
    (legitimate users through, impostor users rejected, their mean; session_accuracy the same over sessions)."""
    sums = table.groupby(CELL + ["kind"]).agg(users=("user", "size"), through=("through", "sum"),
                                              passed=("passed", "sum"), tested=("tested", "sum")).unstack("kind")
    cells = pd.DataFrame({
        "legit_users": sums["users"]["legitimate"], "legit_accepted": sums["through"]["legitimate"],
        "impostor_users": sums["users"]["impostor"], "impostors_through": sums["through"]["impostor"],
        "legit_sessions_passed": sums["passed"]["legitimate"], "legit_sessions_tested": sums["tested"]["legitimate"],
        "impostor_sessions_passed": sums["passed"]["impostor"],
        "impostor_sessions_tested": sums["tested"]["impostor"],
    }).reset_index()
    cells["legitimate_accuracy"] = cells["legit_accepted"] / cells["legit_users"]
    cells["impostor_accuracy"] = 1 - cells["impostors_through"] / cells["impostor_users"]
    cells["accuracy"] = (cells["legitimate_accuracy"] + cells["impostor_accuracy"]) / 2
    cells["session_accuracy"] = (cells["legit_sessions_passed"] / cells["legit_sessions_tested"] + 1
                                 - cells["impostor_sessions_passed"] / cells["impostor_sessions_tested"]) / 2
    cells["split"] = cells["n_impostor"].astype(str) + " x " + cells["n_legitimate"].astype(str)
    return cells.round(4)


def style(ax) -> None:
    ax.set_facecolor(BACKGROUND)
    ax.grid(color="0.88", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors="0.4", labelsize=9)
    ax.set_ylim(-0.04, 1.04)


def plot_experiment1(cells: pd.DataFrame, splits: list[str], best: float, path: Path, seed: int) -> None:
    """Three panels (legitimate, impostor, mean accuracy) against sensitivity, one line per split."""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6.4), sharey=True, facecolor=BACKGROUND)
    top = cells["sensitivity"].max()
    for ax, (column, title, note) in zip(axes, METRICS):
        for i, split in enumerate(splits):
            part = cells[cells["split"] == split].sort_values("sensitivity")
            ax.plot(part["sensitivity"], part[column], color=COLORS[i], marker=MARKERS[i], markersize=4,
                    markeredgecolor="white", linewidth=2, label=split)
        if column == "accuracy":
            ax.axhline(0.5, color="0.5", linestyle="--", linewidth=1, zorder=0)
        style(ax)
        ax.set_xlim(0, top)
        ax.set_xticks(np.arange(0, top + 1e-9, 0.1))
        ax.set_xticks(np.arange(0, top + 1e-9, 0.01), minor=True)
        ax.set_xlabel("Sensitivity (0.01 steps)", fontsize=11)
        ax.set_title(f"{title}\n({note})", loc="left", fontsize=12)
    axes[0].set_ylabel("Accuracy", fontsize=11)
    axes[-1].legend(title="I x L", loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.suptitle(f"Experiment 1 - user x user x sensitivity (seed {seed}, 1 session per user)", x=0.01, ha="left",
                 fontsize=13)
    fig.text(0.01, 0.01, f"One point per sensitivity step of 0.01. Best sensitivity (highest mean accuracy over the "
                         f"{len(splits)} splits): {best:g}, used in experiment 2.", fontsize=9, color="0.3")
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(path, dpi=130, facecolor=BACKGROUND)
    plt.close(fig)


def short_tests(table: pd.DataFrame, sessions: list[int]) -> str:
    """Legitimate users tested on fewer than k sessions (pool too small after the library), e.g. 'user9: 42 at 45'."""
    rows = table[(table["kind"] == "legitimate") & table["sessions"].isin(sessions)
                 & (table["tested"] < table["sessions"])].drop_duplicates(["user", "sessions"])
    parts = []
    for user, group in rows.sort_values("sessions").groupby("user", sort=False):
        counts = [f"{r.tested} at {r.sessions}" for r in group.itertuples()]
        parts.append(f"{user}: {' and '.join(counts)}{' sessions' if len(counts) > 1 else ''}")
    return "; ".join(parts)


def identical_lines(cells: pd.DataFrame, sensitivities: list[float]) -> list[float]:
    """Sensitivities whose three accuracies equal the highest sensitivity's in every split and session count."""
    key = ["split", "sessions"]
    columns = [m[0] for m in METRICS]
    last = cells[cells["sensitivity"] == sensitivities[-1]].set_index(key)[columns].sort_index()
    return [s for s in sensitivities[:-1]
            if cells[cells["sensitivity"] == s].set_index(key)[columns].sort_index().equals(last)]


def plot_experiment2(cells: pd.DataFrame, table: pd.DataFrame, splits: list[str], path: Path, seed: int) -> None:
    """Grid: one column per split, rows legitimate / impostor / mean accuracy against sessions, one line per
    sensitivity."""
    sensitivities = sorted(cells["sensitivity"].unique())
    sessions = sorted(cells["sessions"].unique())
    fig, axes = plt.subplots(3, len(splits), figsize=(5 * len(splits), 12.7), sharex=True, sharey=True,
                             squeeze=False, facecolor=BACKGROUND)
    for col, split in enumerate(splits):
        for row, (column, title, note) in enumerate(METRICS):
            ax = axes[row, col]
            for i, sensitivity in enumerate(sensitivities):
                part = cells[(cells["split"] == split) & (cells["sensitivity"] == sensitivity)].sort_values("sessions")
                ax.plot(part["sessions"], part[column], color=COLORS[i % len(COLORS)], marker=MARKERS[i % len(MARKERS)],
                        markersize=6, markeredgecolor="white", linewidth=2, label=f"{sensitivity:.2f}")
            if column == "accuracy":
                ax.axhline(0.5, color="0.5", linestyle="--", linewidth=1, zorder=0)
            style(ax)
            ax.set_xticks(sessions)
            if col == 0:
                ax.set_ylabel(f"Accuracy\n({ROW_LABELS[row]})", fontsize=11)
            if row == 2:
                ax.set_xlabel("Sessions", fontsize=11)
        axes[0, col].set_title(split, fontsize=13)
    axes[0, -1].legend(title="sensitivity", loc="upper left", bbox_to_anchor=(1.02, 1.02), frameon=False)
    fig.suptitle(f"Experiment 2 - user x session x sensitivity (seed {seed})   -   columns: I x L = impostor users "
                 f"x legitimate users", x=0.01, ha="left", fontsize=13)
    notes = ["Library = a legitimate user's first k sessions. Tested: their last k sessions, or only the sessions "
             "after the library when fewer than k are left"]
    short = short_tests(table, sessions)
    notes[0] += f" ({short})." if short else "."
    notes.append("Impostors: their first k sessions against the legitimate library that passes most of them.")
    same = identical_lines(cells, sensitivities)
    if same:
        names = ", ".join(f"{s:.2f}" for s in same)
        notes[-1] += (f" {names} and {sensitivities[-1]:.2f} give identical results at every session count, so they "
                      f"lie under the {sensitivities[-1]:.2f} line.")
    fig.text(0.01, 0.005, "\n".join(notes), fontsize=9, color="0.3")
    fig.tight_layout(rect=(0, 0.035, 1, 0.975))
    fig.savefig(path, dpi=130, facecolor=BACKGROUND)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ holding accuracy.csv "
                                                "(default: the one config.yaml selects)")
    args = parser.parse_args()
    config = cfg_mod.load_config()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(config).split("/")[0])
    source = group / "accuracy.csv"
    if not source.exists():
        raise SystemExit(f"No {source}: run 10_plot_accuracy.py {group.name} first")

    table = pd.read_csv(source)
    seed = cfg_mod.load_config(group / table["run"].iloc[0] / "config.yaml")["seed"]
    splits = [f"{impostor} x {legit}" for legit, impostor in config["splits"]]
    cells = score_cells(table)
    cells = cells[cells["split"].isin(splits)].copy()
    cells["x"] = cells["split"].map({s: i for i, s in enumerate(splits)})
    cells = cells.sort_values(["x", "sensitivity", "sessions"]).reset_index(drop=True)
    missing = set(splits) - set(cells["split"])
    if missing:
        raise SystemExit(f"accuracy.csv has no runs for split(s) {sorted(missing)} (I x L) of config.yaml's splits")

    exp1 = cells[cells["sessions"] == 1]
    mean = exp1.groupby("sensitivity", as_index=False)[["accuracy", "session_accuracy"]].mean().round(4)
    best = mean.sort_values(["accuracy", "session_accuracy", "sensitivity"],
                            ascending=[False, False, True]).iloc[0]["sensitivity"]
    first, last, step = config["initial_sessions"]
    sessions = list(range(first, last + 1, step))
    wanted = [round(s, 4) for s in config["initial_sensitivities"]]
    exp2 = cells[cells["sessions"].isin(sessions) & cells["sensitivity"].round(4).isin(wanted)]

    out = group / "initial_results"
    out.mkdir(exist_ok=True)
    cells.to_csv(out / "all_settings.csv", index=False)
    exp1.to_csv(out / "exp1_user_user_sensitivity.csv", index=False)
    mean.to_csv(out / "exp1_mean_over_experiments.csv", index=False)
    exp1[exp1["sensitivity"] == best].to_csv(out / "exp1_best_sensitivity_per_experiment.csv", index=False)
    exp2.to_csv(out / "exp2_user_session_sensitivity.csv", index=False)
    plot_experiment1(exp1, splits, best, out / "exp1_user_user_sensitivity.png", seed)
    plot_experiment2(exp2, table, splits, out / "exp2_user_session_sensitivity.png", seed)

    print(exp1[exp1["sensitivity"] == best][["split", "legitimate_accuracy", "impostor_accuracy", "accuracy"]]
          .to_string(index=False))
    print(f"Splits: {len(splits)}  Experiment 1: {exp1['sensitivity'].nunique()} sensitivities, best {best:g}  "
          f"Experiment 2: {exp2['sensitivity'].nunique()} sensitivities x {exp2['sessions'].nunique()} session counts")
    print(f"Output: {out}/")


if __name__ == "__main__":
    main()
