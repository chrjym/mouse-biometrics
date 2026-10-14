#!/usr/bin/env python3
"""Find the sessions: score every experiment at its chosen sensitivity (from 09) with 2, 4, ... profile sessions, then draw the sessions x sensitivity heatmap."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
sens_mod = import_module("09_find_sensitivity")


def heatmap(grid: pd.DataFrame, chosen: dict, title: str, path) -> None:
    """One panel per experiment: profile sessions x sensitivity (sensitivity_values); colour = impostors through /
    impostors (formerly threshold), 0-1. The chosen sensitivity of each experiment is marked with *."""
    experiments = sorted(grid["experiment"].unique(), key=lambda e: int(e[1:]))
    levels = np.round(np.arange(0, 1.01, 0.1), 1)
    n_cols = min(2, len(experiments))
    n_rows = -(-len(experiments) // n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6.2 * n_cols, 3.6 * n_rows + 0.8), squeeze=False)
    for ax, experiment in zip(axes.flat, experiments):
        part = grid[grid["experiment"] == experiment]
        values = part.pivot(index="sessions", columns="sensitivity", values="impostor_sensitivity")
        image = ax.imshow(values.to_numpy(), cmap="YlOrRd", norm=BoundaryNorm(levels, 256), origin="lower", aspect="auto")
        for r, k in enumerate(values.index):
            for c, tolerance in enumerate(values.columns):
                row = part[(part["sessions"] == k) & (part["sensitivity"] == tolerance)].iloc[0]
                ax.text(c, r, f"{row.impostor_sensitivity:.2f}\n({row.impostors_through} of {row.n_impostor})\n"
                              f"legit {row.legit_accepted}/{row.n_legit}", ha="center", va="center", fontsize=7)
        ax.set_xticks(range(len(values.columns)),
                      [f"{t:g}*" if t == chosen[experiment] else f"{t:g}" for t in values.columns])
        ax.set_yticks(range(len(values.index)), values.index)
        ax.set_xlabel("sensitivity (dtw_tolerance; * = chosen by 09)")
        ax.set_ylabel("profile sessions per legitimate user")
        ax.set_title(f"{experiment}: L={part.n_legit.iloc[0]}, I={part.n_impostor.iloc[0]}", fontsize=10)
    for ax in axes.flat[len(experiments):]:
        ax.set_visible(False)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.colorbar(image, ax=axes, ticks=levels, label="sensitivity: impostors through / impostors (0 = best)", shrink=0.8)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    chosen_path = run / "results" / "sensitivity" / "chosen.csv"
    if not chosen_path.exists():
        raise SystemExit(f"No {chosen_path}; run 09_find_sensitivity.py first")
    chosen = pd.read_csv(chosen_path).set_index("experiment")["sensitivity"].to_dict()
    users, order = sens_mod.draw(config, config["seed"])
    print(f"Seed {config['seed']}: users {', '.join(users)}; sessions {config['session_values']}; "
          f"chosen sensitivity {chosen}")
    match_mod.load_cache()
    rows = []
    for k in config["session_values"]:
        for tolerance in config["sensitivity_values"]:
            matrix = sens_mod.pass_matrix(users, order, k, tolerance, config)
            rows += sens_mod.score(users, matrix, config, sensitivity=tolerance, sessions=k)
        print(f"{k} sessions done", flush=True)
    match_mod.save_cache()

    by_experiment = lambda c: c.str[1:].astype(int) if c.name == "experiment" else c
    grid = pd.DataFrame(rows).sort_values(["sessions", "experiment", "sensitivity"], key=by_experiment)
    table = grid[grid.apply(lambda r: chosen[r["experiment"]] == r["sensitivity"], axis=1)]
    out = run / "results" / "session"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "experiments.csv", index=False)
    grid.to_csv(out / "grid.csv", index=False)
    figures = run / "figures"
    title = f"users {', '.join(users)}, seed {config['seed']}"
    sens_mod.line_plots(table, "sessions", "sessions", f"Find the sessions (chosen sensitivity per experiment): {title}",
                        figures / "find_session.png")
    heatmap(grid, chosen, f"Sensitivity per session count and sensitivity value\n{title}", figures / "sensitivity_heatmap.png")

    for r in table.itertuples():
        print(f"{r.sessions:2} sessions {r.experiment} (tol {r.sensitivity:g}): legit {r.legit_accepted}/{r.n_legit}, "
              f"impostors through {r.impostors_through}/{r.n_impostor}, accuracy {r.accuracy:.2f}")
    print(f"Output: {out / 'experiments.csv'}, {out / 'grid.csv'}, {figures / 'find_session.png'}, {figures / 'sensitivity_heatmap.png'}")


if __name__ == "__main__":
    main()
