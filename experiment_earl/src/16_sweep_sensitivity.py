#!/usr/bin/env python3
"""Sensitivity sweep of config.yaml's sweep keys: DTW distances once, then a confusion matrix (positive = impostor) per split x sessions x sensitivity, overall and per legitimate user -> runs/<hash>/sweep/."""

import argparse
import pickle
from importlib import import_module
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from numba import njit, prange

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("08_plot_matches")

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = cfg_mod.CACHE_DIR / "distances.pkl"
_DIST: dict = {}  # (query session, library session, segmentation, band) -> {kind: best DTW distance per query chunk}


@njit(cache=True)
def _dtw_cost(a, b, band, cap, prev, cur):
    """Banded DTW cost between paths a and b, or inf once every cell exceeds `cap`."""
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
def best_distance(queries, library, band, cap):
    """Per query path: smallest DTW cost to any library path (inf if none is within `cap`)."""
    n = queries.shape[1]
    best = np.full(queries.shape[0], np.inf)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            cost = _dtw_cost(queries[q], library[k], band, min(cap, best[q]), prev, cur)
            if cost < best[q]:
                best[q] = cost
    return best


def load_plan() -> dict:
    """The sweep keys of config.yaml (00_config.SWEEP_KEYS, left out of the run hash) plus its seed."""
    config = cfg_mod.load_config()
    missing = [key for key in cfg_mod.SWEEP_KEYS if key not in config]
    if missing:
        raise SystemExit(f"config.yaml has no {', '.join(missing)}")
    for legit, impostor in config["splits"]:
        if legit + impostor > len(cfg_mod.list_users(config)):
            raise SystemExit(f"Split [{legit}, {impostor}] needs {legit + impostor} users; the data has fewer")
    start, stop, step = config["sweep_sensitivity"]
    return {"seed": config["seed"], "splits": config["splits"], "max_sessions": config["sweep_sessions_max"],
            "test_sessions": config["sweep_test_sessions"],
            "sensitivities": np.round(np.arange(start, stop + step / 2, step), 4)}


def pair_distance(query, library, config: dict, cap: float) -> dict[int, np.ndarray]:
    """Best per-point DTW distance of every query chunk to the library session's chunks of the same kind."""
    n = config["resample_n"]
    key = (query.key, library.key, match_mod.segmentation(config), config["dtw_band"], cap)
    if key not in _DIST:
        band = int(round(config["dtw_band"] * n))
        _DIST[key] = {kind: best_distance(paths, library.paths[kind], band, cap * n) / n
                      if len(paths) and len(library.paths[kind]) else np.full(len(paths), np.inf)
                      for kind, paths in query.paths.items()}
    return _DIST[key]


def session_curve(query, library: list, config: dict, cap: float) -> np.ndarray:
    """(chunks, k) best distance of each query chunk to the first 1..k library sessions (running minimum)."""
    columns = [np.concatenate([pair_distance(query, lib, config, cap)[kind] for kind in query.paths]) for lib in library]
    return np.minimum.accumulate(np.stack(columns, axis=1), axis=1)


def accepted(curve: np.ndarray, n_chunks: int, sensitivities: np.ndarray, ratio: float) -> np.ndarray:
    """(k, sensitivity) bool: does the session pass a k-session library at each sensitivity?"""
    matched = (curve[:, :, None] <= sensitivities[None, None, :]).sum(axis=0)
    return matched / max(n_chunks, 1) >= ratio


def sweep_split(legit_n: int, impostor_n: int, plan: dict, base: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per (sessions, sensitivity) with TP/FP/FN/TN over test sessions and over users."""
    config = {**base, "seed": plan["seed"], "n_legitimate": legit_n, "n_impostor": impostor_n}
    legit, impostor, order = plot_mod.draw_users(config, plan["seed"])
    m, t = plan["max_sessions"], plan["test_sessions"]
    sens, cap = plan["sensitivities"], float(plan["sensitivities"].max())
    ratio, through = config["match_shape_ratio"], config["match_session_ratio"]
    session = lambda user, item: match_mod.dataset_session(user, item[1], config, item[0])
    libraries = {u: [session(u, s) for s in order[u][:m]] for u in legit}

    def verdicts(user: str, tests: list, profiles: list[str]) -> np.ndarray:
        """(sessions tested x profiles, k, sensitivity): one attempt per (session, profile) pair."""
        out = []
        for item in tests:
            query = session(user, item)
            out.extend(accepted(session_curve(query, libraries[p], config, cap), query.n_chunks, sens, ratio)
                       for p in profiles)
        return np.array(out)

    # Legitimate: own last t sessions (never in a library) against own library; impostor: first t against each library
    # as a separate attempt, so an impostor session gets one chance per attempt, like a legitimate session.
    legit_acc = {u: verdicts(u, order[u][-t:], [u]) for u in legit}
    impostor_acc = {u: verdicts(u, order[u][:t], legit) for u in impostor}
    attempts = impostor_n * t * legit_n  # impostor (session, profile) pairs
    tn = sum(a.sum(axis=0) for a in legit_acc.values())
    fn = sum(a.sum(axis=0) for a in impostor_acc.values())
    users_tn = sum(a.mean(axis=0) >= through for a in legit_acc.values())
    users_fn = sum(a.mean(axis=0) >= through for a in impostor_acc.values())

    k, s = np.meshgrid(np.arange(1, m + 1), sens, indexing="ij")
    table = pd.DataFrame({"n_legitimate": legit_n, "n_impostor": impostor_n, "sessions": k.ravel(), "sensitivity": s.ravel(),
                          "TP": (attempts - fn).ravel(), "FP": (legit_n * t - tn).ravel(),
                          "FN": fn.ravel(), "TN": tn.ravel(),
                          "users_TP": (impostor_n - users_fn).ravel(), "users_FP": (legit_n - users_tn).ravel(),
                          "users_FN": users_fn.ravel(), "users_TN": users_tn.ravel()})
    table["accuracy"] = (table["TP"] + table["TN"]) / (attempts + legit_n * t)
    table["FAR"] = table["FN"] / attempts            # impostor attempts let in
    table["FRR"] = table["FP"] / (legit_n * t)      # legitimate sessions rejected
    table["balanced_accuracy"] = 1 - (table["FAR"] + table["FRR"]) / 2
    table["users_accuracy"] = (table["users_TP"] + table["users_TN"]) / (legit_n + impostor_n)
    table["legitimate"] = ",".join(legit)
    table["impostor"] = ",".join(impostor)
    return table, user_table(legit_n, impostor_n, legit, legit_acc, impostor_acc, k, s)


def user_table(legit_n: int, impostor_n: int, legit: list[str], legit_acc: dict, impostor_acc: dict,
               k: np.ndarray, s: np.ndarray) -> pd.DataFrame:
    """One confusion matrix per (legitimate user, half, sessions, sensitivity): the user's own test sessions and every
    impostor attempt against the user's library. Test sessions alternate between halves (even = pick, odd = check),
    so 18 can choose a setting on one half and score it on sessions it never saw."""
    rows = []
    for p, u in enumerate(legit):
        genuine = legit_acc[u]
        attacks = np.concatenate([a[p::legit_n] for a in impostor_acc.values()])  # attempts are (session, profile)
        for half, start in (("pick", 0), ("check", 1)):
            g, a = genuine[start::2], attacks[start::2]
            tn, fn = g.sum(axis=0), a.sum(axis=0)
            rows.append(pd.DataFrame({"n_legitimate": legit_n, "n_impostor": impostor_n, "user": u, "half": half,
                                      "sessions": k.ravel(), "sensitivity": s.ravel(),
                                      "TP": (len(a) - fn).ravel(), "FP": (len(g) - tn).ravel(),
                                      "FN": fn.ravel(), "TN": tn.ravel()}))
    table = pd.concat(rows, ignore_index=True)
    table["FAR"] = table["FN"] / (table["TP"] + table["FN"])
    table["FRR"] = table["FP"] / (table["FP"] + table["TN"])
    table["balanced_accuracy"] = 1 - (table["FAR"] + table["FRR"]) / 2
    return table


def load_cache() -> None:
    if CACHE_PATH.exists():
        _DIST.update(pickle.loads(CACHE_PATH.read_bytes()))


def save_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump(_DIST, f)
    tmp.replace(CACHE_PATH)


def out_folder(plan: dict, base: dict) -> Path:
    """runs/<hash>/sweep/, the hash of config.yaml without its sweep keys (same rule as every other run)."""
    return cfg_mod.RUNS / cfg_mod.run_folder_name({**base, "seed": plan["seed"]}).split("/")[0] / "sweep"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    plan, base = load_plan(), cfg_mod.load_config()
    if plan["max_sessions"] + plan["test_sessions"] > cfg_mod.max_sessions(base):
        raise SystemExit(f"sweep_sessions_max + sweep_test_sessions = {plan['max_sessions'] + plan['test_sessions']} "
                         f"exceeds the smallest pool ({cfg_mod.max_sessions(base)}); lower them in config.yaml")
    folder = out_folder(plan, base)
    (folder / "parts").mkdir(parents=True, exist_ok=True)
    (folder / "config.yaml").write_text(yaml.safe_dump(base, sort_keys=False))
    load_cache()
    parts, users = [], []
    for legit_n, impostor_n in plan["splits"]:
        path = folder / "parts" / f"{legit_n}_{impostor_n}.csv"
        user_path = folder / "parts" / f"{legit_n}_{impostor_n}_users.csv"
        if path.exists() and user_path.exists():  # finished earlier: resume
            parts.append(pd.read_csv(path))
            users.append(pd.read_csv(user_path))
            continue
        part, user_part = sweep_split(legit_n, impostor_n, plan, base)
        save_cache()
        for frame, target in ((part, path), (user_part, user_path)):
            frame.to_csv(target.with_suffix(".tmp"), index=False)
            target.with_suffix(".tmp").replace(target)
        parts.append(part)
        users.append(user_part)
        print(f"[{legit_n} L, {impostor_n} I] done")
    out = folder / "confusion.csv"
    pd.concat(parts).to_csv(out, index=False)
    pd.concat(users).to_csv(folder / "user_confusion.csv", index=False)
    print(f"{len(plan['splits'])} splits x {plan['max_sessions']} sessions x {len(plan['sensitivities'])} sensitivities "
          f"= {sum(len(p) for p in parts)} confusion matrices\nOutput: {out}")


if __name__ == "__main__":
    main()
