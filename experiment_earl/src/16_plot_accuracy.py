#!/usr/bin/env python3
"""Sessions that go through (fixed counts, as in the notebook), per user, for every run under runs/<hash>/: one figure per split and sensitivity with legitimate and impostor line graphs."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MaxNLocator

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")

ROOT = Path(__file__).resolve().parents[1]


def score(user: str, sessions: list[tuple[str, str]], library: list, config: dict) -> dict:
    """Sessions of `user` that pass (>= match_shape_ratio of their strokes match the library), plus the strokes."""
    passed = matched = strokes = 0
    for folder, name in sessions:
        session = match_mod.dataset_session(user, name, config, folder)
        hits = match_mod.matched_chunks(session, library, config)
        passed += hits / max(session.n_chunks, 1) >= config["match_shape_ratio"]
        matched += hits
        strokes += session.n_chunks
    return {"passed": passed, "tested": len(sessions), "matched_strokes": matched, "strokes": strokes}


def score_run(folder: Path) -> list[dict]:
    """Legitimate: own last sessions_per_user pool sessions (never in a profile) against own profile. Impostor: first
    sessions_per_user sessions (the notebook's) against the legitimate profile that passes most of them."""
    config = cfg_mod.load_config(folder / "config.yaml")
    k = config["sessions_per_user"]
    legit, impostor, order = plot_mod.draw_users(config, config["seed"])
    libraries = {u: [match_mod.dataset_session(u, n, config, f) for f, n in order[u][:k]] for u in legit}
    run = {"run": folder.name, "sensitivity": config["sensitivity"], "sessions": k,
           "n_legitimate": config["n_legitimate"], "n_impostor": config["n_impostor"]}
    rows = []
    for user in legit:
        rows.append({**run, "kind": "legitimate", "user": user, "profile": user,
                     **score(user, order[user][-k:], libraries[user], config)})
    for user in impostor:
        scores = {p: score(user, order[user][:k], lib, config) for p, lib in libraries.items()}
        profile = max(scores, key=lambda p: (scores[p]["passed"], scores[p]["matched_strokes"] / max(scores[p]["strokes"], 1)))
        rows.append({**run, "kind": "impostor", "user": user, "profile": profile, **scores[profile]})
    for row in rows:
        row["through"] = row["passed"] >= config["match_session_ratio"] * row["tested"]
    return rows


def plot(table: pd.DataFrame, path: Path, title: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True,
                             gridspec_kw={"width_ratios": [max(table[table.kind == k].user.nunique(), 2)
                                                           for k in ("legitimate", "impostor")]})
    sessions = sorted(table["sessions"].unique())
    colours = plt.cm.viridis([0.85 * i / max(len(sessions) - 1, 1) for i in range(len(sessions))])
    for ax, kind in zip(axes, ("legitimate", "impostor")):
        part = table[table["kind"] == kind]
        users = sorted(part["user"].unique(), key=lambda u: int(u[4:]))
        for k, g in part.groupby("sessions"):
            g = g.set_index("user").reindex(users)
            colour = colours[sessions.index(k)]
            ax.plot(users, g["passed"], color=colour, label=f"{k} sessions")
            ax.scatter(users, g["passed"], s=36, zorder=3, edgecolors=colour,
                       facecolors=[colour if t else "white" for t in g["through"].fillna(False)])
        ax.set_title(f"{kind.capitalize()} users", fontsize=10)
        ax.set_xlabel(f"{kind} user")
        ax.set_ylim(-0.3, max(sessions) + 0.3)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("sessions that go through")
    axes[1].legend(fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.suptitle(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ holding the runs to compare "
                                                "(default: the one config.yaml selects)")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    folders = sorted(p.parent for p in group.glob("*/config.yaml"))
    if not folders:
        raise SystemExit(f"No runs under {group}")

    match_mod.load_cache()
    rows = []
    for folder in folders:
        rows += score_run(folder)
        print(f"{folder.name} done", flush=True)
    match_mod.save_cache()

    table = pd.DataFrame(rows)
    table.to_csv(group / "accuracy.csv", index=False)
    config = cfg_mod.load_config(folders[0] / "config.yaml")
    figures = []
    for (n_legit, n_impostor, sens), part in table.groupby(["n_legitimate", "n_impostor", "sensitivity"]):
        path = group / f"accuracy_{n_legit}_{n_impostor}_sensitivity_{sens:g}.png"
        plot(part, path,
             f"runs/{group.name}, {n_legit} legitimate vs {n_impostor} impostors, sensitivity {sens:g}: sessions that go through (≥ {config['match_shape_ratio']:.0%} of strokes "
             f"match), seed {config['seed']}\nlegitimate = own last <sessions> sessions (never in a profile) vs own profile; "
             f"impostor = first <sessions> sessions vs the best legitimate profile; line = sessions per user; "
             f"filled = user goes through (≥ {config['match_session_ratio']:.0%} of sessions)")
        figures.append(path.name)

    summary = table.groupby(["n_legitimate", "n_impostor", "kind", "sensitivity", "sessions"]).agg(passed=("passed", "sum"), tested=("tested", "sum"),
                                                                     through=("through", "sum"), users=("user", "size"))
    print(summary.to_string())
    print(f"Runs: {len(folders)}  Rows: {len(table)}")
    print(f"Output: {group / 'accuracy.csv'}, {', '.join(figures)}")


if __name__ == "__main__":
    main()
