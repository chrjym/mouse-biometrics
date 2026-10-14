#!/usr/bin/env python3
"""Match each legitimate user's own unused sessions against their own profile, next to the impostors' sessions, per session step of the notebook."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")


def score(user: str, sessions: list[tuple[str, str]], library: list, kind: str, profile: str, k: int,
          config: dict) -> list[dict]:
    """Share of each session's strokes that match the profile's library, and whether it reaches `match_shape_ratio`."""
    rows = []
    for folder, name in sessions:
        session = match_mod.dataset_session(user, name, config, folder)
        ratio = match_mod.matched_chunks(session, library, config) / max(session.n_chunks, 1)
        rows.append({"profile": profile, "sessions": k, "kind": kind, "user": user, "session": name,
                     "strokes": session.n_chunks,
                     "ratio": round(ratio, 4), "matched": ratio >= config["match_shape_ratio"]})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--held-out", type=int, default=2,
                        help="unused sessions per legitimate user to test (the next ones after sessions_per_user)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    legit, impostor, order = plot_mod.draw_users(config, config["seed"])
    steps = list(range(1, config["sessions_per_user"] + 1))
    held_out = {u: order[u][config["sessions_per_user"]:][:args.held_out] for u in legit}
    print(f"Seed {config['seed']}: legitimate {', '.join(legit)}; impostors {', '.join(impostor)}; "
          f"profile = first 1..{steps[-1]} sessions; genuine = next {args.held_out} sessions, never in the profile")
    match_mod.load_cache()

    rows = []
    for profile in legit:
        for k in steps:
            library = [match_mod.dataset_session(profile, n, config, f) for f, n in order[profile][:k]]
            rows += score(profile, held_out[profile], library, "genuine", profile, k, config)
            for user in impostor:
                rows += score(user, order[user][:k], library, "impostor", profile, k, config)
        print(f"{profile} done", flush=True)
    match_mod.save_cache()

    table = pd.DataFrame(rows)
    results = run / "results"
    results.mkdir(exist_ok=True)
    table.to_csv(results / "genuine_check.csv", index=False)
    summary = (table.groupby(["profile", "sessions", "kind"], sort=False)
               .agg(mean_ratio=("ratio", "mean"), passed=("matched", "sum"), tested=("matched", "size")).reset_index())
    summary.round(4).to_csv(results / "genuine_check_summary.csv", index=False)

    n_cols = min(3, len(legit))
    n_rows = -(-len(legit) // n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4.3 * n_cols, 3.4 * n_rows), sharey=True, squeeze=False)
    x = np.arange(len(steps))
    for ax, profile in zip(axes.flat, legit):
        g = summary[summary["profile"] == profile]
        for offset, kind, colour in ((-0.2, "genuine", "tab:blue"), (0.2, "impostor", "tab:red")):
            part = g[g["kind"] == kind].set_index("sessions").reindex(steps)
            bars = ax.bar(x + offset, part["mean_ratio"], 0.4, color=colour, label=kind)
            ax.bar_label(bars, labels=[f"{p:.0f}/{t:.0f}" for p, t in zip(part["passed"], part["tested"])],
                         padding=2, fontsize=7)
        ax.axhline(config["match_shape_ratio"], color="k", linestyle=":", linewidth=1)
        ax.set_title(f"{profile} (genuine: {len(held_out[profile])} unused sessions)", fontsize=9)
        ax.set_xticks(x, [str(k) for k in steps])
        ax.set_xlabel("sessions in the profile")
    for ax in axes[:, 0]:
        ax.set_ylabel("share of strokes matched")
    for ax in axes.flat[len(legit):]:
        ax.set_visible(False)
    axes[0, 0].legend(fontsize=8, loc="upper left")
    fig.suptitle(f"Own unused sessions (blue) vs impostors {', '.join(impostor)} (red) against each legitimate profile, "
                 f"seed {config['seed']}\nbar = mean share of strokes matched; label = sessions passed "
                 f"(≥ {config['match_shape_ratio']:.0%}, dotted line) / sessions tested", fontsize=9)
    fig.tight_layout()
    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    fig.savefig(figures / "genuine_check.png", dpi=130)
    plt.close(fig)

    for profile in legit:
        g = summary[summary["profile"] == profile]
        line = " | ".join(f"{k}: own {r_g.passed:.0f}/{r_g.tested:.0f} ({r_g.mean_ratio:.0%}), "
                          f"impostor {r_i.passed:.0f}/{r_i.tested:.0f} ({r_i.mean_ratio:.0%})"
                          for k in steps
                          for r_g in [g[(g["sessions"] == k) & (g["kind"] == "genuine")].iloc[0]]
                          for r_i in [g[(g["sessions"] == k) & (g["kind"] == "impostor")].iloc[0]])
        print(f"{profile}: {line}")
    print(f"Output: {results / 'genuine_check.csv'}, {results / 'genuine_check_summary.csv'}, {figures / 'genuine_check.png'}")


if __name__ == "__main__":
    main()
