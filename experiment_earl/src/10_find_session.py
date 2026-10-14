#!/usr/bin/env python3
"""Find the sessions: score every experiment E_k at its chosen sensitivity (from 09) with 2, 4, ... profile sessions, then draw the sensitivity heatmap."""

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


def heatmap(table: pd.DataFrame, title: str, path) -> None:
    """Sessions x experiment; colour = impostor sensitivity (formerly threshold: impostors through / impostors), 0-1."""
    grid = table.pivot(index="sessions", columns="experiment", values="impostor_sensitivity")
    grid = grid[sorted(grid.columns, key=lambda e: int(e[1:]))]
    levels = np.round(np.arange(0, 1.01, 0.1), 1)
    fig, ax = plt.subplots(figsize=(1.4 * len(grid.columns) + 2.5, 0.7 * len(grid.index) + 2))
    image = ax.imshow(grid.to_numpy(), cmap="YlOrRd", norm=BoundaryNorm(levels, 256), origin="lower", aspect="auto")
    for r, k in enumerate(grid.index):
        for c, experiment in enumerate(grid.columns):
            row = table[(table["sessions"] == k) & (table["experiment"] == experiment)].iloc[0]
            ax.text(c, r, f"{row.impostor_sensitivity:.2f}\n({row.impostors_through} of {row.n_impostor})\n"
                          f"legit {row.legit_accepted}/{row.n_legit}", ha="center", va="center", fontsize=8)
    labels = [f"{e}\nL={table[table.experiment == e].n_legit.iloc[0]}, "
              f"I={table[table.experiment == e].n_impostor.iloc[0]}\ntol {table[table.experiment == e].sensitivity.iloc[0]:g}"
              for e in grid.columns]
    ax.set_xticks(range(len(grid.columns)), labels, fontsize=8)
    ax.set_yticks(range(len(grid.index)), grid.index)
    ax.set_xlabel("experiment (legitimate / impostor users, chosen sensitivity)")
    ax.set_ylabel("profile sessions per legitimate user")
    ax.set_title(title, fontsize=10)
    fig.colorbar(image, ax=ax, ticks=levels, label="sensitivity: impostors through / impostors (0 = best)")
    fig.tight_layout()
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
        for tolerance in sorted(set(chosen.values())):
            matrix = sens_mod.pass_matrix(users, order, k, tolerance, config)
            rows += [r for r in sens_mod.score(users, matrix, config, sensitivity=tolerance, sessions=k)
                     if chosen[r["experiment"]] == tolerance]
        print(f"{k} sessions done", flush=True)
    match_mod.save_cache()

    table = pd.DataFrame(rows)
    table = table.sort_values(["sessions", "experiment"], key=lambda c: c.str[1:].astype(int) if c.name == "experiment" else c)
    out = run / "results" / "session"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "experiments.csv", index=False)
    figures = run / "figures"
    title = f"users {', '.join(users)}, seed {config['seed']}"
    sens_mod.line_plots(table, "sessions", "sessions", f"Find the sessions (chosen sensitivity per experiment): {title}",
                        figures / "find_session.png")
    heatmap(table, f"Sensitivity per experiment and session count\n{title}", figures / "sensitivity_heatmap.png")

    for r in table.itertuples():
        print(f"{r.sessions:2} sessions {r.experiment} (tol {r.sensitivity:g}): legit {r.legit_accepted}/{r.n_legit}, "
              f"impostors through {r.impostors_through}/{r.n_impostor}, accuracy {r.accuracy:.2f}")
    print(f"Output: {out / 'experiments.csv'}, {figures / 'find_session.png'}, {figures / 'sensitivity_heatmap.png'}")


if __name__ == "__main__":
    main()
