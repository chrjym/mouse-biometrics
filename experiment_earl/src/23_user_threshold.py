#!/usr/bin/env python3
"""Per-user DTW threshold, with and without size normalization. Each stroke's nearest banded-DTW cost to a profile is
computed once; a user's threshold is the q-quantile of their own enrollment strokes' nearest cost to their other
enrollment sessions. Chosen per split on a training seed, then applied unchanged to test seeds; writes
runs/user_threshold/{summary,best,test}.csv."""

import argparse
from importlib import import_module

import numpy as np
import pandas as pd
from numba import njit, prange

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
plot_mod = import_module("14_plot_matches")

OUT = cfg_mod.RUNS / "user_threshold"
SIZE_SCALE = 500.0  # px per unit when stroke size is kept, so costs stay near the normalized range
MAX_COST = 0.15     # mean cost per point above which two strokes count as unrelated (inf)
_SESSIONS: dict = {}
_NEAREST: dict = {}


@njit(cache=True)
def _dtw_capped(a, b, band, cap, prev, cur):
    """Banded DTW cost of a and b, or inf once every cell of a row exceeds `cap`."""
    n = a.shape[0]
    prev[:] = np.inf
    prev[0] = 0.0
    for i in range(n):
        cur[:] = np.inf
        row_min = np.inf
        for j in range(max(0, i - band), min(n - 1, i + band) + 1):
            dx, dy = a[i, 0] - b[j, 0], a[i, 1] - b[j, 1]
            value = np.sqrt(dx * dx + dy * dy) + min(prev[j], prev[j + 1], cur[j])
            cur[j + 1] = value
            row_min = min(row_min, value)
        if row_min > cap:
            return np.inf
        prev, cur = cur, prev
    return prev[n]


@njit(parallel=True, cache=True)
def nearest(queries, library, band, cap):
    """Per query path: the smallest DTW cost to any library path (inf if all exceed `cap`)."""
    n = queries.shape[1]
    out = np.full(queries.shape[0], np.inf)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        best = cap
        for k in range(library.shape[0]):
            cost = _dtw_capped(queries[q], library[k], band, best, prev, cur)
            if cost < best:
                best = cost
        if best < cap:
            out[q] = best
    return out


def shape(chunk: np.ndarray, n: int, keep_size: bool) -> np.ndarray | None:
    """Normalized as in 03, or start at the origin with the real size kept (px / SIZE_SCALE)."""
    if not keep_size:
        return chunk_mod.normalize(chunk, n)
    xy = chunk[:, :2] - chunk[0, :2]
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    if arc[-1] == 0:
        return None
    grid = np.linspace(0, arc[-1], n)
    return np.column_stack([np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])]) / SIZE_SCALE


def session(user: str, folder: str, name: str, keep_size: bool, config: dict) -> tuple[int, dict]:
    """(number of strokes, kind -> (m, n, 2) shapes) for one session."""
    key = (user, name, keep_size)
    if key not in _SESSIONS:
        chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / folder / user / name), config)
        paths = {}
        for kind in (chunk_mod.MOVE, chunk_mod.DRAG):
            shapes = [shape(c, config["resample_n"], keep_size) for c, k in chunks if k == kind]
            paths[kind] = np.array([s for s in shapes if s is not None]).reshape(-1, config["resample_n"], 2)
        _SESSIONS[key] = (len(chunks), paths)
    return _SESSIONS[key]


def nearest_to(query: tuple, library: list[tuple], config: dict) -> np.ndarray:
    """Mean cost per point of each query stroke to its nearest same-kind stroke in any library session."""
    n = config["resample_n"]
    band = int(round(config["dtw_band"] * n))
    costs = []
    for kind in (chunk_mod.MOVE, chunk_mod.DRAG):
        paths = query[1][kind]
        best = np.full(len(paths), np.inf)
        for lib in library:
            pair = (id(query), id(lib), kind)
            if pair not in _NEAREST:
                _NEAREST[pair] = (nearest(paths, lib[1][kind], band, MAX_COST * n) / n
                                  if len(paths) and len(lib[1][kind]) else np.full(len(paths), np.inf))
            best = np.minimum(best, _NEAREST[pair])
        costs.append(best)
    return np.concatenate(costs)


def evaluate(seed: int, keep_size: bool, sessions: list[int], quantiles: list[float], config: dict) -> pd.DataFrame:
    """User-level results for every split, sessions per user and quantile of one seed."""
    users = cfg_mod.list_users(config)
    order = {u: cfg_mod.session_pool(config, u, seed) for u in users}
    load = lambda u, items: [session(u, f, name, keep_size, config) for f, name in items]
    rows = []
    for k in sessions:
        enrolled = {u: load(u, order[u][:k]) for u in users}
        own = {u: np.concatenate([nearest_to(s, enrolled[u][:i] + enrolled[u][i + 1:], config)
                                  for i, s in enumerate(enrolled[u])]) for u in users}
        tested = {(u, role): load(u, order[u][-k:] if role == "legitimate" else order[u][:k])
                  for u in users for role in ("legitimate", "impostor")}
        cost = {(u, role, p): [(nearest_to(s, enrolled[p], config), s[0]) for s in tested[(u, role)]]
                for u in users for role in ("legitimate", "impostor") for p in users if (role == "legitimate") == (u == p)}
        for q in quantiles:
            threshold = {u: np.quantile(own[u][np.isfinite(own[u])], q) if np.isfinite(own[u]).any() else 0.0
                         for u in users}
            passed = {key: sum((c <= threshold[key[2]]).sum() / max(m, 1) >= config["match_shape_ratio"]
                               for c, m in value) for key, value in cost.items()}
            for n_legit in range(1, len(users)):
                legit, impostor, _ = plot_mod.draw_users({**config, "n_legitimate": n_legit,
                                                          "n_impostor": len(users) - n_legit}, seed)
                run = {"seed": seed, "size": "kept" if keep_size else "normalized", "quantile": q, "sessions": k,
                       "n_legitimate": n_legit}
                for u in legit:
                    rows.append({**run, "kind": "legitimate", "passed": passed[(u, "legitimate", u)]})
                for u in impostor:
                    rows.append({**run, "kind": "impostor", "passed": max(passed[(u, "impostor", p)] for p in legit)})
        print(f"seed {seed}, size {'kept' if keep_size else 'normalized'}, {k} sessions done", flush=True)
    table = pd.DataFrame(rows)
    table["through"] = table["passed"] >= config["match_session_ratio"] * table["sessions"]
    keys = ["seed", "size", "quantile", "sessions", "n_legitimate"]
    rate = table.pivot_table(index=keys, columns="kind", values="through", aggfunc="mean").reset_index()
    rate["user_accuracy"] = (rate["legitimate"] + 1 - rate["impostor"]) / 2
    return rate.rename(columns={"legitimate": "legitimate_rate", "impostor": "impostor_rate"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-seed", type=int, default=927)
    parser.add_argument("--test-seeds", type=int, nargs="+", default=[928, 929, 930])
    parser.add_argument("--sessions", type=int, nargs="+", default=[2, 4, 6, 8])
    parser.add_argument("--quantiles", type=float, nargs="+", default=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8])
    args = parser.parse_args()

    config = cfg_mod.load_config()
    summary = pd.concat([evaluate(seed, keep, args.sessions, args.quantiles, config)
                         for keep in (False, True) for seed in [args.train_seed] + args.test_seeds])
    train = summary[summary["seed"] == args.train_seed]
    best = train.sort_values("user_accuracy", ascending=False).groupby(["size", "n_legitimate"]).head(1)
    test = summary[summary["seed"] != args.train_seed].merge(
        best[["size", "n_legitimate", "quantile", "sessions"]], on=["size", "n_legitimate", "quantile", "sessions"])
    report = best.set_index(["size", "n_legitimate"])[["quantile", "sessions", "user_accuracy", "impostor_rate",
                                                        "legitimate_rate"]].join(
        test.groupby(["size", "n_legitimate"]).agg(test_accuracy=("user_accuracy", "mean"),
                                                   test_impostor_rate=("impostor_rate", "mean"),
                                                   test_legitimate_rate=("legitimate_rate", "mean")))

    OUT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT / "summary.csv", index=False)
    report.to_csv(OUT / "best.csv")
    test.to_csv(OUT / "test.csv", index=False)
    print(report.round(2).to_string())
    print(f"Output: {OUT}")


if __name__ == "__main__":
    main()
