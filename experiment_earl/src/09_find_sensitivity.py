#!/usr/bin/env python3
"""Find the sensitivity: score every experiment in `experiments` (legitimate x impostor user counts, set by hand) at every sensitivity (DTW tolerance) in sensitivity_values."""

import argparse
import random
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")


def draw(config: dict, seed: int) -> tuple[list[str], dict[str, list[tuple[str, str]]]]:
    """Every user in one seeded random order, and the shuffled session pool of each user an experiment needs."""
    users = cfg_mod.list_users(config)
    for n_legit, n_impostor in config["experiments"]:
        if n_legit < 1 or n_impostor < 1 or n_legit + n_impostor > len(users):
            raise SystemExit(f"experiments entry [{n_legit}, {n_impostor}]: need at least 1 of each and at most "
                             f"{len(users)} users in total; change it in config.yaml")
    need = profile_max(config) + config["test_sessions"]
    if need > cfg_mod.max_sessions(config):
        raise SystemExit(f"Need {need} sessions per user (profile + test_sessions) but some user has only "
                         f"{cfg_mod.max_sessions(config)}; lower session_values or test_sessions in config.yaml")
    drawn = random.Random(seed).sample(users, max(l + i for l, i in config["experiments"]))
    return drawn, {user: cfg_mod.session_pool(config, user, seed) for user in drawn}


def profile_max(config: dict) -> int:
    return max(config["session_values"] + [config["sensitivity_sessions"]])


def experiments(users: list[str], config: dict) -> list[tuple[str, list[str], list[str]]]:
    """E1, E2, ... in config order: [L, I] takes the first L drawn users as legitimate and the next I as impostors."""
    return [(f"E{i}", users[:n_legit], users[n_legit:n_legit + n_impostor])
            for i, (n_legit, n_impostor) in enumerate(config["experiments"], start=1)]


def test_part(pool: list[tuple[str, str]], config: dict) -> list[tuple[str, str]]:
    """The tested sessions: the next `test_sessions` after the largest profile, so they are never in a profile."""
    start = profile_max(config)
    return pool[start:start + config["test_sessions"]]


def pass_matrix(users: list[str], order: dict, k: int, tolerance: float, config: dict) -> dict[tuple[str, str], bool]:
    """(profile, user) -> does `user` go through `profile`'s first-k-session library at this sensitivity?
    A test session matches when at least `match_shape_ratio` of its strokes match; a user goes through when at
    least `match_session_ratio` of their test sessions match."""
    config = {**config, "sensitivity": tolerance}
    load = lambda user, part: [match_mod.dataset_session(user, name, config, folder) for folder, name in part]
    tests = {user: load(user, test_part(order[user], config)) for user in users}
    matrix = {}
    for profile in users:
        library = load(profile, order[profile][:k])
        for user in users:
            hits = [match_mod.matched_chunks(s, library, config) / max(s.n_chunks, 1) >= config["match_shape_ratio"]
                    for s in tests[user]]
            matrix[(profile, user)] = sum(hits) / len(hits) >= config["match_session_ratio"]
    return matrix


def score(users: list[str], matrix: dict, config: dict, **columns) -> list[dict]:
    """One row per experiment. Legitimate accuracy: share of legitimate users whose own test sessions pass their own
    profile. Impostor accuracy: share of impostors that no legitimate profile lets through."""
    rows = []
    for name, legit, impostor in experiments(users, config):
        accepted = sum(matrix[(u, u)] for u in legit)
        through = sum(any(matrix[(p, u)] for p in legit) for u in impostor)
        legit_acc, impostor_acc = accepted / len(legit), 1 - through / len(impostor)
        rows.append({"experiment": name, "n_legit": len(legit), "n_impostor": len(impostor), **columns,
                     "legitimate": ",".join(legit), "impostors": ",".join(impostor),
                     "legit_accepted": accepted, "impostors_through": through,
                     "legit_accuracy": round(legit_acc, 4), "impostor_accuracy": round(impostor_acc, 4),
                     "accuracy": round((legit_acc + impostor_acc) / 2, 4),
                     "impostor_sensitivity": round(through / len(impostor), 4)})
    return rows


def line_plots(table: pd.DataFrame, line: str, label: str, title: str, path: Path) -> None:
    """Separate legitimate and impostor graphs: accuracy against the number of users, one line per `line` value.
    Experiments with the same number of users on an axis are averaged into one point."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    markers = "osD^vP*X"
    for i, (value, group) in enumerate(table.groupby(line)):
        for ax, x, y in ((axes[0], "n_legit", "legit_accuracy"), (axes[1], "n_impostor", "impostor_accuracy")):
            g = group.groupby(x)[y].mean()
            ax.plot(g.index, g.to_numpy(), marker=markers[i % len(markers)], label=f"{label} {value:g}", alpha=0.85)
    for ax, x, name in ((axes[0], "n_legit", "legitimate"), (axes[1], "n_impostor", "impostor")):
        ax.set_xticks(sorted(table[x].unique()))
        ax.set_xlabel(f"{name} users (L)" if name == "legitimate" else f"{name} users (I)")
        ax.set_title(f"{name.capitalize()}: " + ("own sessions accepted" if name == "legitimate" else "impostors rejected"))
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
    users, order = draw(config, config["seed"])
    k = config["sensitivity_sessions"]
    print(f"Seed {config['seed']}: users in draw order {', '.join(users)}; experiments [L, I] {config['experiments']}; profile = first {k} sessions, "
          f"test = next {config['test_sessions']} after session {profile_max(config)}")
    match_mod.load_cache()
    rows = []
    for tolerance in config["sensitivity_values"]:
        rows += score(users, pass_matrix(users, order, k, tolerance, config), config, sensitivity=tolerance, sessions=k)
        print(f"sensitivity {tolerance:g} done", flush=True)
    match_mod.save_cache()

    table = pd.DataFrame(rows)
    # Per experiment, the sensitivity with the best mean of legitimate and impostor accuracy (ties: the stricter one).
    chosen = table.sort_values(["experiment", "accuracy", "sensitivity"], ascending=[True, False, True]) \
        .groupby("experiment").head(1).sort_values("experiment", key=lambda e: e.str[1:].astype(int))
    out = run / "results" / "sensitivity"
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "experiments.csv", index=False)
    chosen.to_csv(out / "chosen.csv", index=False)
    figure = run / "figures" / "find_sensitivity.png"
    line_plots(table, "sensitivity", "sensitivity", f"Find the sensitivity: users {', '.join(users)}, {k} profile "
               f"sessions, seed {config['seed']}", figure)

    for r in chosen.itertuples():
        print(f"{r.experiment} (L={r.n_legit}, I={r.n_impostor}): sensitivity {r.sensitivity:g}, "
              f"legit {r.legit_accepted}/{r.n_legit}, impostors through {r.impostors_through}/{r.n_impostor}, "
              f"accuracy {r.accuracy:.2f}")
    print(f"Output: {out / 'experiments.csv'}, {out / 'chosen.csv'}, {figure}")


if __name__ == "__main__":
    main()
