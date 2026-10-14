#!/usr/bin/env python3
"""Find the sensitivity: score the n_legitimate legitimate users and n_impostor impostors of the seed's draw at the configured sensitivity, user by user."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")

HELD_OUT = 2  # tested sessions per user: the next ones after sessions_per_user, never in a profile (as in 15)


def draw(config: dict) -> tuple[list[str], list[str], dict, dict]:
    """The notebook's draw (legitimate users in draw order, sorted impostors, session orders) and each user's tested
    sessions."""
    need = config["sessions_per_user"] + HELD_OUT
    if need > cfg_mod.max_sessions(config):
        raise SystemExit(f"Need {need} sessions per user (sessions_per_user + {HELD_OUT} tested) but some user has only "
                         f"{cfg_mod.max_sessions(config)}; lower sessions_per_user in config.yaml")
    legit, impostor, order = plot_mod.draw_users(config, config["seed"])
    k = config["sessions_per_user"]
    return legit, impostor, order, {u: order[u][k:k + HELD_OUT] for u in legit + impostor}


def session_hits(legit: list[str], users: list[str], order: dict, tests: dict, k: int, sensitivity: float,
                 config: dict) -> dict[tuple[str, str], list[bool]]:
    """(profile, user) -> per tested session of `user`: does it match `profile`'s first-k-session library
    (at least `match_shape_ratio` of its strokes within `sensitivity`)?"""
    config = {**config, "sensitivity": sensitivity}
    load = lambda user, part: [match_mod.dataset_session(user, name, config, folder) for folder, name in part]
    sessions = {user: load(user, tests[user]) for user in users}
    hits = {}
    for profile in legit:
        library = load(profile, order[profile][:k])
        for user in users:
            hits[(profile, user)] = [match_mod.matched_chunks(s, library, config) / max(s.n_chunks, 1)
                                     >= config["match_shape_ratio"] for s in sessions[user]]
    return hits


def user_rows(legit: list[str], impostor: list[str], hits: dict, config: dict, **columns) -> list[dict]:
    """One row per user. Legitimate: accuracy = share of own tested sessions that match the own profile; accepted when
    that share reaches `match_session_ratio`. Impostor: accuracy = share of tested sessions no legitimate profile
    matches; through when some profile matches at least `match_session_ratio` of them."""
    rows = []
    for user in legit:
        own = hits[(user, user)]
        accepted = bool(np.mean(own) >= config["match_session_ratio"])
        rows.append({"role": "legitimate", "user": user, **columns, "accuracy": round(float(np.mean(own)), 4),
                     "sessions_correct": f"{sum(own)}/{len(own)}", "passed": accepted,
                     "matched_by": user if accepted else ""})
    for user in impostor:
        matched_by = [p for p in legit if np.mean(hits[(p, user)]) >= config["match_session_ratio"]]
        rejected = [not any(hits[(p, user)][i] for p in legit) for i in range(len(hits[(legit[0], user)]))]
        rows.append({"role": "impostor", "user": user, **columns, "accuracy": round(float(np.mean(rejected)), 4),
                     "sessions_correct": f"{sum(rejected)}/{len(rejected)}", "passed": bool(matched_by),
                     "matched_by": ",".join(matched_by)})
    return rows


def summarize(rows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Per `keys`: legitimate accuracy = legitimate users accepted / legitimate users; impostor accuracy = impostors
    not through / impostors; sensitivity (formerly threshold) = impostors through / impostors."""
    out = []
    for key, g in rows.groupby(keys, sort=False):
        legit, impostor = g[g.role == "legitimate"], g[g.role == "impostor"]
        legit_acc, through = legit.passed.mean(), impostor.passed.mean()
        out.append({**dict(zip(keys, key if isinstance(key, tuple) else (key,))),
                    "legit_accepted": int(legit.passed.sum()), "n_legit": len(legit),
                    "impostors_through": int(impostor.passed.sum()), "n_impostor": len(impostor),
                    "legit_accuracy": round(legit_acc, 4), "impostor_accuracy": round(1 - through, 4),
                    "accuracy": round((legit_acc + 1 - through) / 2, 4), "impostor_sensitivity": round(through, 4)})
    return pd.DataFrame(out)


def line_plots(rows: pd.DataFrame, line: str, label: str, title: str, path: Path) -> None:
    """Separate legitimate and impostor graphs: accuracy per user (x), one line per `line` value."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    markers = "osD^vP*X"
    for ax, role in zip(axes, ("legitimate", "impostor")):
        part = rows[rows.role == role]
        users = list(dict.fromkeys(part.user))
        for i, (value, g) in enumerate(part.groupby(line)):
            g = g.set_index("user").reindex(users)
            ax.plot(range(len(users)), g.accuracy, marker=markers[i % len(markers)], label=f"{label} {value:g}",
                    alpha=0.85)
        ax.set_xticks(range(len(users)), users, rotation=30)
        ax.set_xlim(-0.5, max(len(users) - 0.5, 0.5))
        ax.set_xlabel(f"{role} users ({'L' if role == 'legitimate' else 'I'})")
        ax.set_title("Legitimate: own sessions accepted" if role == "legitimate" else "Impostor: sessions rejected")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("accuracy")
    axes[1].legend(fontsize=8)
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    print(cfg_mod.describe_data(config))
    legit, impostor, order, tests = draw(config)
    k, sensitivity = config["sessions_per_user"], config["sensitivity"]
    print(f"Seed {config['seed']}: legitimate {', '.join(legit)}; impostors {', '.join(impostor)}; "
          f"profile = first {k} sessions, tested = next {HELD_OUT}; sensitivity {sensitivity:g}")
    match_mod.load_cache()
    hits = session_hits(legit, legit + impostor, order, tests, k, sensitivity, config)
    match_mod.save_cache()

    rows = pd.DataFrame(user_rows(legit, impostor, hits, config, sensitivity=sensitivity, sessions=k))
    summary = summarize(rows, ["sensitivity", "sessions"])
    out = run / "results" / "sensitivity"
    out.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out / "users.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    figure = run / "figures" / "find_sensitivity.png"
    line_plots(rows, "sensitivity", "sensitivity", f"Find the sensitivity: {k} profile sessions, seed {config['seed']}",
               figure)

    for r in rows.itertuples():
        print(f"{r.role:10} {r.user:7} accuracy {r.accuracy:.2f} ({r.sessions_correct} sessions), "
              f"{'accepted' if r.role == 'legitimate' else 'through'}: {r.passed}")
    s = summary.iloc[0]
    print(f"sensitivity {sensitivity:g}: legit {s.legit_accepted:.0f}/{s.n_legit:.0f} accepted, impostors through "
          f"{s.impostors_through:.0f}/{s.n_impostor:.0f}, accuracy {s.accuracy:.2f}")
    print(f"Output: {out / 'users.csv'}, {out / 'summary.csv'}, {figure}")


if __name__ == "__main__":
    main()
