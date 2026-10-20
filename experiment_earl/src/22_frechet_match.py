#!/usr/bin/env python3
"""Discrete Fréchet matching in place of DTW: two strokes match when the largest point gap of their best alignment is
at most `epsilon` (bounding-box diagonal = 1). Scored with 16's rules on every split of one draw; writes
runs/frechet/<seed>/{accuracy,summary,best}.csv."""

import argparse
from importlib import import_module

import numpy as np
import pandas as pd
from numba import njit, prange

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")

OUT = cfg_mod.RUNS / "frechet"


@njit(cache=True)
def _frechet_within(a, b, band, eps, prev, cur):
    """True if the banded discrete Fréchet distance between paths a and b is at most `eps`."""
    n = a.shape[0]
    prev[:] = np.inf
    prev[0] = 0.0
    for i in range(n):
        cur[:] = np.inf
        row_min = np.inf
        for j in range(max(0, i - band), min(n - 1, i + band) + 1):
            dx, dy = a[i, 0] - b[j, 0], a[i, 1] - b[j, 1]
            value = max(np.sqrt(dx * dx + dy * dy), min(prev[j], prev[j + 1], cur[j]))
            cur[j + 1] = value
            row_min = min(row_min, value)
        if row_min > eps:
            return False
        prev, cur = cur, prev
    return prev[n] <= eps


@njit(parallel=True, cache=True)
def has_match(queries, library, band, eps):
    """Per query path: does any library path lie within Fréchet distance `eps`?"""
    n = queries.shape[1]
    found = np.zeros(queries.shape[0], dtype=np.bool_)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            if _frechet_within(queries[q], library[k], band, eps, prev, cur):
                found[q] = True
                break
    return found


def passed(user: str, sessions: list[tuple[str, str]], library: list, eps: float, config: dict) -> int:
    """Sessions of `user` with >= match_shape_ratio of their strokes matching a same-kind stroke of the library."""
    band = int(round(config["dtw_band"] * config["resample_n"]))
    count = 0
    for folder, name in sessions:
        query = match_mod.dataset_session(user, name, config, folder)
        hits = 0
        for kind, paths in query.paths.items():
            found = np.zeros(len(paths), dtype=bool)
            for session in library:
                if len(paths) and len(session.paths[kind]):
                    found |= has_match(paths, session.paths[kind], band, eps)
            hits += int(found.sum())
        count += hits / max(query.n_chunks, 1) >= config["match_shape_ratio"]
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=927)
    parser.add_argument("--epsilons", type=float, nargs="+", default=[0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3])
    parser.add_argument("--sessions", type=int, nargs="+", default=[2, 4, 6, 8, 10])
    args = parser.parse_args()

    config = cfg_mod.load_config(seed=args.seed)
    users = cfg_mod.list_users(config)
    order = {u: cfg_mod.session_pool(config, u, args.seed) for u in users}
    scores, rows = {}, []
    for eps in args.epsilons:
        for k in args.sessions:
            libraries = {u: [match_mod.dataset_session(u, n, config, f) for f, n in order[u][:k]] for u in users}

            def score(user, role, profile):
                key = (user, role, profile, eps, k)
                if key not in scores:
                    tested = order[user][-k:] if role == "legitimate" else order[user][:k]
                    scores[key] = passed(user, tested, libraries[profile], eps, config)
                return scores[key]

            for n_legit in range(1, len(users)):
                legit, impostor, _ = plot_mod.draw_users({**config, "n_legitimate": n_legit,
                                                          "n_impostor": len(users) - n_legit}, args.seed)
                run = {"epsilon": eps, "sessions": k, "n_legitimate": n_legit, "n_impostor": len(users) - n_legit}
                for u in legit:
                    rows.append({**run, "kind": "legitimate", "user": u, "profile": u,
                                 "passed": score(u, "legitimate", u), "tested": k})
                for u in impostor:
                    profile = max(legit, key=lambda p: score(u, "impostor", p))
                    rows.append({**run, "kind": "impostor", "user": u, "profile": profile,
                                 "passed": score(u, "impostor", profile), "tested": k})
            print(f"epsilon {eps}, {k} sessions done", flush=True)

    table = pd.DataFrame(rows)
    table["through"] = table["passed"] >= config["match_session_ratio"] * table["tested"]
    keys = ["n_legitimate", "n_impostor", "epsilon", "sessions"]
    summary = table.pivot_table(index=keys, columns="kind", values="through", aggfunc=["sum", "count", "mean"])
    summary.columns = [f"{kind}_{ {'sum': 'through', 'count': 'users', 'mean': 'rate'}[stat] }" for stat, kind in summary.columns]
    summary = summary.reset_index()
    summary["user_accuracy"] = (summary["legitimate_rate"] + 1 - summary["impostor_rate"]) / 2
    best = summary.sort_values("user_accuracy", ascending=False).groupby("n_legitimate").head(1).sort_values("n_legitimate")

    out = OUT / str(args.seed)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "accuracy.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    best.to_csv(out / "best.csv", index=False)
    print(table.pivot_table(index="epsilon", columns="kind", values="through", aggfunc="mean").round(3).to_string())
    print(best.to_string(index=False))
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
