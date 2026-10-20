#!/usr/bin/env python3
"""Template selection at enrollment: build each legitimate profile from its best strokes only (quality filter,
consistency across the user's own sessions, k DTW medoids), then score it with 16's rules. Writes
runs/template_selection/<seed>/{accuracy,summary,best}.csv."""

import argparse
from importlib import import_module

import numpy as np
import pandas as pd
from numba import njit, prange

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("14_plot_matches")

OUT = cfg_mod.RUNS / "template_selection"
VARIANTS = {  # name -> (min_straightness, other own sessions a stroke must recur in, medoids per kind)
    "all": (None, None, None),
    "straight>=1.02": (1.02, None, None),
    "straight>=1.05": (1.05, None, None),
    "straight>=1.10": (1.10, None, None),
    "recur>=1": (None, 1, None),
    "medoids": (None, None, (40, 10)),
    "straight>=1.05+recur>=1": (1.05, 1, None),
    "straight>=1.05+recur>=1+medoids": (1.05, 1, (40, 10)),
}


@njit(cache=True)
def _dtw_cost(a, b, band):
    """Full banded DTW cost between paths a and b (no early abandoning)."""
    n = a.shape[0]
    prev, cur = np.full(n + 1, np.inf), np.full(n + 1, np.inf)
    prev[0] = 0.0
    for i in range(n):
        cur[:] = np.inf
        for j in range(max(0, i - band), min(n - 1, i + band) + 1):
            dx, dy = a[i, 0] - b[j, 0], a[i, 1] - b[j, 1]
            cur[j + 1] = np.sqrt(dx * dx + dy * dy) + min(prev[j], prev[j + 1], cur[j])
        prev, cur = cur, prev
    return prev[n]


@njit(parallel=True, cache=True)
def _cost_matrix(paths, band):
    m = paths.shape[0]
    out = np.zeros((m, m))
    for i in prange(m):
        for j in range(i + 1, m):
            out[i, j] = _dtw_cost(paths[i], paths[j], band)
    return out + out.T


def straightness(paths: np.ndarray) -> np.ndarray:
    """Path length / start-to-end distance per normalized path (1 = a straight line)."""
    arc = np.hypot(*np.moveaxis(np.diff(paths, axis=1), 2, 0)).sum(axis=1)
    chord = np.hypot(*(paths[:, -1] - paths[:, 0]).T)
    return np.where(chord > 0, arc / np.maximum(chord, 1e-12), np.inf)


def medoids(paths: np.ndarray, k: int, band: int, rounds: int = 10) -> np.ndarray:
    """k-medoids (farthest-first start, then alternate assign / re-centre) on the DTW cost matrix."""
    if len(paths) <= k:
        return paths
    cost = _cost_matrix(paths, band)
    chosen = [int(cost.sum(axis=1).argmin())]
    while len(chosen) < k:
        chosen.append(int(cost[:, chosen].min(axis=1).argmax()))
    for _ in range(rounds):
        group = cost[:, chosen].argmin(axis=1)
        new = [int(np.flatnonzero(group == g)[cost[np.ix_(group == g, group == g)].sum(axis=1).argmin()])
               for g in range(k)]
        if new == chosen:
            break
        chosen = new
    return paths[chosen]


def select(user: str, sessions: list, variant: str, config: dict) -> chunk_mod.Session:
    """One library Session holding the user's selected strokes per kind."""
    min_straight, min_recur, per_kind = VARIANTS[variant]
    n = config["resample_n"]
    band, cap = int(round(config["dtw_band"] * n)), config["sensitivity"] * n
    library = chunk_mod.Session(f"{user}/selected", sum(s.n_chunks for s in sessions))
    for kind in (chunk_mod.MOVE, chunk_mod.DRAG):
        kept = []
        for i, session in enumerate(sessions):
            paths = session.paths[kind]
            if min_straight is not None and len(paths):
                paths = paths[straightness(paths) >= min_straight]
            if min_recur is not None and len(paths):
                others = [s.paths[kind] for j, s in enumerate(sessions) if j != i and len(s.paths[kind])]
                seen = sum((match_mod.has_match(paths, o, band, cap).astype(int) for o in others),
                           np.zeros(len(paths), dtype=int))
                paths = paths[seen >= min_recur]
            kept.append(paths)
        paths = np.concatenate(kept) if kept else np.empty((0, n, 2))
        if per_kind is not None and len(paths):
            paths = medoids(paths, per_kind[kind], band)
        library.paths[kind] = paths.reshape(-1, n, 2)
    return library


def passed(user: str, sessions: list[tuple[str, str]], library: chunk_mod.Session, config: dict) -> int:
    """Sessions of `user` with >= match_shape_ratio of their strokes matching the selected library (16's rule)."""
    n = config["resample_n"]
    band, cap = int(round(config["dtw_band"] * n)), config["sensitivity"] * n
    count = 0
    for folder, name in sessions:
        query = match_mod.dataset_session(user, name, config, folder)
        hits = sum(int(match_mod.has_match(p, library.paths[kind], band, cap).sum())
                   for kind, p in query.paths.items() if len(p) and len(library.paths[kind]))
        count += hits / max(query.n_chunks, 1) >= config["match_shape_ratio"]
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=927)
    parser.add_argument("--sensitivities", type=float, nargs="+", default=[0.02, 0.03, 0.04])
    parser.add_argument("--sessions", type=int, nargs="+", default=[4, 6, 8, 10])
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    args = parser.parse_args()

    base = cfg_mod.load_config(seed=args.seed)
    users = cfg_mod.list_users(base)
    order = {u: cfg_mod.session_pool(base, u, args.seed) for u in users}
    libraries, scores, rows = {}, {}, []
    for sens in args.sensitivities:
        config = {**base, "sensitivity": sens}
        for k in args.sessions:
            for variant in args.variants:
                sizes = []
                for n_legit in range(1, len(users)):
                    legit, impostor, _ = plot_mod.draw_users({**config, "n_legitimate": n_legit,
                                                              "n_impostor": len(users) - n_legit}, args.seed)
                    for u in legit:
                        if (u, sens, k, variant) not in libraries:
                            sessions = [match_mod.dataset_session(u, name, config, f) for f, name in order[u][:k]]
                            libraries[(u, sens, k, variant)] = select(u, sessions, variant, config)
                            sizes.append(sum(len(p) for p in libraries[(u, sens, k, variant)].paths.values()))

                    def score(user, role, profile):
                        key = (user, role, profile, sens, k, variant)
                        if key not in scores:
                            tested = order[user][-k:] if role == "legitimate" else order[user][:k]
                            scores[key] = passed(user, tested, libraries[(profile, sens, k, variant)], config)
                        return scores[key]

                    run = {"sensitivity": sens, "sessions": k, "variant": variant,
                           "n_legitimate": n_legit, "n_impostor": len(users) - n_legit}
                    for u in legit:
                        rows.append({**run, "kind": "legitimate", "user": u, "profile": u,
                                     "passed": score(u, "legitimate", u), "tested": k})
                    for u in impostor:
                        profile = max(legit, key=lambda p: score(u, "impostor", p))
                        rows.append({**run, "kind": "impostor", "user": u, "profile": profile,
                                     "passed": score(u, "impostor", profile), "tested": k})
                print(f"sensitivity {sens:.2f}, {k} sessions, {variant}: library strokes "
                      f"{min(sizes, default=0)}-{max(sizes, default=0)}", flush=True)

    table = pd.DataFrame(rows)
    table["through"] = table["passed"] >= base["match_session_ratio"] * table["tested"]
    keys = ["n_legitimate", "n_impostor", "variant", "sensitivity", "sessions"]
    summary = table.pivot_table(index=keys, columns="kind", values="through", aggfunc=["sum", "count", "mean"])
    summary.columns = [f"{kind}_{stat}" for stat, kind in summary.columns]
    summary = summary.rename(columns=lambda c: c.replace("_sum", "_through").replace("_count", "_users")
                             .replace("_mean", "_rate")).reset_index()
    summary["user_accuracy"] = (summary["legitimate_rate"] + 1 - summary["impostor_rate"]) / 2
    best = summary.sort_values("user_accuracy", ascending=False).groupby(["n_legitimate", "variant"]).head(1)

    out = OUT / str(args.seed)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / "accuracy.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    best.sort_values(["variant", "n_legitimate"]).to_csv(out / "best.csv", index=False)
    print(best.pivot_table(index="n_legitimate", columns="variant", values="user_accuracy").round(2).to_string())
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
