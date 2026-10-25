#!/usr/bin/env python3
"""Match each legitimate user's own unused sessions against their own profile, next to the impostors' sessions, per session step of the notebook."""

import argparse
from importlib import import_module

import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("08_plot_matches")


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

    for profile in legit:
        g = summary[summary["profile"] == profile]
        line = " | ".join(f"{k}: own {r_g.passed:.0f}/{r_g.tested:.0f} ({r_g.mean_ratio:.0%}), "
                          f"impostor {r_i.passed:.0f}/{r_i.tested:.0f} ({r_i.mean_ratio:.0%})"
                          for k in steps
                          for r_g in [g[(g["sessions"] == k) & (g["kind"] == "genuine")].iloc[0]]
                          for r_i in [g[(g["sessions"] == k) & (g["kind"] == "impostor")].iloc[0]])
        print(f"{profile}: {line}")
    print(f"Output: {results / 'genuine_check.csv'}, {results / 'genuine_check_summary.csv'}")


if __name__ == "__main__":
    main()
