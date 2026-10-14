#!/usr/bin/env python3
"""Find the sessions: score the same users at the sensitivity from 09 with 1, 2, ... sessions_per_user profile sessions, then draw the sensitivity heatmap."""

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


def heatmap_rows(legit: list[str], impostor: list[str], hits: dict, k: int, config: dict) -> list[dict]:
    """Sensitivity (formerly threshold) = impostors through / impostors, with the first 1, 2, ... legitimate users'
    profiles (draw order, as in the notebook's heatmap)."""
    rows = []
    for n in range(1, len(legit) + 1):
        through = sum(any(np.mean(hits[(p, v)]) >= config["match_session_ratio"] for p in legit[:n]) for v in impostor)
        rows.append({"sessions": k, "legit_users": n, "impostors_through": through,
                     "sensitivity": round(through / len(impostor), 4)})
    return rows


def heatmap(grid: pd.DataFrame, n_impostor: int, title: str, path) -> None:
    """Sessions x legitimate users; colour = sensitivity 0-1 in 0.1 steps (0 = best)."""
    values = grid.pivot(index="sessions", columns="legit_users", values="sensitivity")
    through = grid.pivot(index="sessions", columns="legit_users", values="impostors_through")
    levels = np.round(np.arange(0, 1.01, 0.1), 1)
    fig, ax = plt.subplots(figsize=(1.3 * len(values.columns) + 3.5, 0.6 * len(values.index) + 2.2))
    image = ax.imshow(values.to_numpy(), cmap="YlOrRd", norm=BoundaryNorm(levels, 256), origin="lower", aspect="auto")
    for r, k in enumerate(values.index):
        for c, n in enumerate(values.columns):
            ax.text(c, r, f"{values.loc[k, n]:.2f}\n({through.loc[k, n]:.0f} of {n_impostor})", ha="center",
                    va="center", fontsize=8)
    ax.set_xticks(range(len(values.columns)), values.columns)
    ax.set_yticks(range(len(values.index)), values.index)
    ax.set_xlabel("number of legitimate users")
    ax.set_ylabel("profile sessions per legitimate user")
    ax.set_title(title, fontsize=10)
    fig.colorbar(image, ax=ax, ticks=levels, label="sensitivity (0 = best)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    found = run / "results" / "sensitivity" / "summary.csv"
    if not found.exists():
        raise SystemExit(f"No {found}; run 09_find_sensitivity.py first")
    sensitivity = float(pd.read_csv(found)["sensitivity"].iloc[0])
    legit, impostor, order, tests = sens_mod.draw(config)
    steps = list(range(1, config["sessions_per_user"] + 1))
    print(f"Seed {config['seed']}: legitimate {', '.join(legit)}; impostors {', '.join(impostor)}; "
          f"sessions {steps}; sensitivity {sensitivity:g} (from 09)")
    match_mod.load_cache()
    rows, grid = [], []
    for k in steps:
        hits = sens_mod.session_hits(legit, legit + impostor, order, tests, k, sensitivity, config)
        rows += sens_mod.user_rows(legit, impostor, hits, config, sensitivity=sensitivity, sessions=k)
        grid += heatmap_rows(legit, impostor, hits, k, config)
    match_mod.save_cache()

    rows, grid = pd.DataFrame(rows), pd.DataFrame(grid)
    summary = sens_mod.summarize(rows, ["sessions"])
    out = run / "results" / "session"
    out.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out / "users.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    grid.to_csv(out / "heatmap.csv", index=False)
    figures = run / "figures"
    title = f"sensitivity {sensitivity:g}, seed {config['seed']}"
    sens_mod.line_plots(rows, "sessions", "sessions", f"Find the sessions: {title}", figures / "find_session.png")
    heatmap(grid, len(impostor), f"Sensitivity = impostors through / {len(impostor)} impostors\n{title}",
            figures / "sensitivity_heatmap.png")

    for s in summary.itertuples():
        print(f"{s.sessions} sessions: legit {s.legit_accepted}/{s.n_legit} accepted, impostors through "
              f"{s.impostors_through}/{s.n_impostor}, accuracy {s.accuracy:.2f}")
    print(f"Output: {out / 'users.csv'}, {out / 'summary.csv'}, {out / 'heatmap.csv'}, {figures / 'find_session.png'}, "
          f"{figures / 'sensitivity_heatmap.png'}")


if __name__ == "__main__":
    main()
