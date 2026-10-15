#!/usr/bin/env python3
"""Share of strokes that go through, per user, for every run under runs/<hash>/: one figure per sensitivity with legitimate and impostor line graphs."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")

ROOT = Path(__file__).resolve().parents[1]
HELD_OUT = 2  # last sessions of a legitimate user's pool: never in a profile, the same for every run


def stroke_share(user: str, sessions: list[tuple[str, str]], library: list, config: dict) -> tuple[int, int]:
    """(strokes matched by the library, strokes) over all `sessions` of `user`."""
    matched = strokes = 0
    for folder, name in sessions:
        session = match_mod.dataset_session(user, name, config, folder)
        matched += match_mod.matched_chunks(session, library, config)
        strokes += session.n_chunks
    return matched, strokes


def score_run(folder: Path) -> list[dict]:
    """Legitimate: own held-out sessions against own profile. Impostor: first sessions_per_user sessions against
    the legitimate profile that matches most of their strokes (the notebook's best profile)."""
    config = cfg_mod.load_config(folder / "config.yaml")
    k = config["sessions_per_user"]
    legit, impostor, order = plot_mod.draw_users(config, config["seed"])
    libraries = {u: [match_mod.dataset_session(u, n, config, f) for f, n in order[u][:k]] for u in legit}
    run = {"run": folder.name, "sensitivity": config["sensitivity"], "sessions": k,
           "n_legitimate": config["n_legitimate"], "n_impostor": config["n_impostor"]}
    rows = []
    for user in legit:
        matched, strokes = stroke_share(user, order[user][-HELD_OUT:], libraries[user], config)
        rows.append({**run, "kind": "legitimate", "user": user, "profile": user, "matched": matched, "strokes": strokes})
    for user in impostor:
        scores = {p: stroke_share(user, order[user][:k], lib, config) for p, lib in libraries.items()}
        profile = max(scores, key=lambda p: scores[p][0] / max(scores[p][1], 1))
        rows.append({**run, "kind": "impostor", "user": user, "profile": profile,
                     "matched": scores[profile][0], "strokes": scores[profile][1]})
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
            line = g.set_index("user")["accuracy"].reindex(users)
            ax.plot(users, line, marker="o", color=colours[sessions.index(k)], label=f"{k} sessions")
        ax.set_title(f"{kind.capitalize()} users", fontsize=10)
        ax.set_xlabel(f"{kind} user")
        ax.set_ylim(-0.02, 1.02)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("accuracy (share of strokes matched)")
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
    table["accuracy"] = (table["matched"] / table["strokes"].clip(lower=1)).round(4)
    table.to_csv(group / "accuracy.csv", index=False)
    config = cfg_mod.load_config(folders[0] / "config.yaml")
    figures = []
    for sens, part in table.groupby("sensitivity"):
        path = group / f"accuracy_sensitivity_{sens:g}.png"
        plot(part, path,
             f"runs/{group.name}, sensitivity {sens:g}: share of strokes that match a legitimate profile (seed {config['seed']})\n"
             f"legitimate = own last {HELD_OUT} sessions (never in a profile) vs own profile; impostor = first <sessions> "
             f"sessions vs the best-matching legitimate profile; line = sessions per user")
        figures.append(path.name)

    summary = table.groupby(["kind", "sensitivity", "sessions"])["accuracy"].mean().unstack("sessions")
    print(summary.round(3).to_string())
    print(f"Runs: {len(folders)}  Rows: {len(table)}")
    print(f"Output: {group / 'accuracy.csv'}, {', '.join(figures)}")


if __name__ == "__main__":
    main()
