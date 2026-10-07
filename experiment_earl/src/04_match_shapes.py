#!/usr/bin/env python3
"""Match every impostor session against each legitimate profile with banded DTW; writes results/trial_<k>.json."""

import argparse
import json
import pickle
from importlib import import_module
from pathlib import Path

import numpy as np
from numba import njit, prange

cfg_mod = import_module("00_config")
users_mod = import_module("01_sample_users")
sessions_mod = import_module("02_sample_sessions")
chunk_mod = import_module("03_chunk_shapes")

_PAIRS: dict = {}     # (query session, library session, settings) -> {kind: bool array per query chunk}
_SESSIONS: dict = {}  # dataset path -> Session, so grids chunk each file once
CACHE_PATH = cfg_mod.ROOT / "results" / "cache" / "pairs.pkl"


@njit(cache=True)
def _dtw_within(a, b, band, cap, prev, cur):
    """True if the banded DTW cost between paths a and b is at most `cap` (gives up once every cell exceeds it)."""
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
            return False
        prev, cur = cur, prev
    return prev[n] <= cap


@njit(parallel=True, cache=True)
def has_match(queries, library, band, cap):
    """Per query path: does any library path lie within DTW cost `cap`?"""
    n = queries.shape[1]
    found = np.zeros(queries.shape[0], dtype=np.bool_)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            if _dtw_within(queries[q], library[k], band, cap, prev, cur):
                found[q] = True
                break
    return found


def segmentation(config: dict) -> tuple:
    """Settings that change which chunks a session has; part of every cache key."""
    return (config["pause_gap_s"], config["min_points"], config["min_length_px"], config["resample_n"])


def pair_matches(query: chunk_mod.Session, library: chunk_mod.Session, config: dict) -> dict[int, np.ndarray]:
    n = config["resample_n"]
    key = (query.key, library.key, segmentation(config), config["dtw_band"], config["dtw_tolerance"])
    if key not in _PAIRS:
        band, cap = int(round(config["dtw_band"] * n)), config["dtw_tolerance"] * n
        _PAIRS[key] = {
            kind: has_match(paths, library.paths[kind], band, cap) if len(library.paths[kind]) else
            np.zeros(len(paths), dtype=bool)
            for kind, paths in query.paths.items()
        }
    return _PAIRS[key]


def matched_chunks(query: chunk_mod.Session, library: list[chunk_mod.Session], config: dict) -> int:
    """Chunks of `query` (same kind only) that match a chunk in any library session."""
    total = 0
    for kind, paths in query.paths.items():
        found = np.zeros(len(paths), dtype=bool)
        for session in library:
            found |= pair_matches(query, session, config)[kind]
        total += int(found.sum())
    return total


def match_trial(legit: dict[str, list], impostor: dict[str, list], config: dict) -> list[dict]:
    """One record per impostor user. Each legitimate profile is scored separately (`per_profile`);
    the impostor counts as matched if any single profile reaches `match_session_ratio`."""
    records = []
    for user, sessions in impostor.items():
        per_profile = {
            profile: [matched_chunks(s, library, config) / max(s.n_chunks, 1) for s in sessions]
            for profile, library in legit.items()
        }
        share = {p: sum(r >= config["match_shape_ratio"] for r in ratios) / len(ratios)
                 for p, ratios in per_profile.items()}
        best = max(per_profile, key=lambda p: (share[p], np.mean(per_profile[p])))
        records.append({
            "impostor": user,
            "matched": bool(share[best] >= config["match_session_ratio"]),
            "matched_against": best,
            "session_ratios": [round(float(r), 4) for r in per_profile[best]],
            "per_profile": {p: [round(float(r), 4) for r in ratios] for p, ratios in per_profile.items()},
        })
    return records


def sanity_check(legit: dict[str, list], held_out: dict[str, list], config: dict) -> dict[str, list[float]]:
    """Held-out genuine sessions against their own user's library: the ratios should beat the impostors'."""
    return {
        user: [round(matched_chunks(s, legit[user], config) / max(s.n_chunks, 1), 4) for s in sessions]
        for user, sessions in held_out.items() if sessions
    }


def dataset_session(user: str, name: str, config: dict) -> chunk_mod.Session:
    path = cfg_mod.ROOT / config["dataset_dir"] / user / name
    if (path, segmentation(config)) not in _SESSIONS:
        chunks = chunk_mod.segment(cfg_mod.load_session(path), config)
        _SESSIONS[(path, segmentation(config))] = chunk_mod.describe(f"{user}/{name}", chunks, config)
    return _SESSIONS[(path, segmentation(config))]


def run_trial(config: dict, seed: int) -> dict:
    """Draw users and sessions for `seed`, then match; the in-memory version of scripts 01 to 04."""
    legit_users, impostor_users = users_mod.draw_users(config, seed)
    drawn = sessions_mod.draw_sessions(config, seed, legit_users + impostor_users)
    build = lambda user, key: [dataset_session(user, name, config) for name in drawn[user][key]]
    legit = {u: build(u, "sessions") for u in legit_users}
    impostor = {u: build(u, "sessions") for u in impostor_users}
    held_out = {u: build(u, "held_out") for u in legit_users}
    return {
        "seed": seed,
        "legitimate": legit_users,
        "records": match_trial(legit, impostor, config),
        "sanity": sanity_check(legit, held_out, config),
    }


def load_cache() -> None:
    if CACHE_PATH.exists():
        _PAIRS.update(pickle.loads(CACHE_PATH.read_bytes()))


def save_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_bytes(pickle.dumps(_PAIRS))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=int, default=0, help="trial number used in the output file name")
    args = parser.parse_args()
    config = cfg_mod.load_config()
    root = cfg_mod.ROOT
    manifest = json.loads((root / "temp" / "manifest.json").read_text())
    load_cache()

    def sessions(label: str, user: str) -> list:
        folder = root / "shapes" / label / user
        return [chunk_mod.describe(f"{user}/{p.name[:-4]}", chunk_mod.load_chunks(p), config)
                for p in sorted(folder.glob("session_*.npz"))]

    legit = {u: sessions("legitimate", u) for u in manifest["legitimate"]}
    impostor = {u: sessions("impostor", u) for u in manifest["impostor"]}
    held_out = {u: [dataset_session(u, n, config) for n in manifest["sessions"]["legitimate"][u]["held_out"]]
                for u in manifest["legitimate"]}
    records = match_trial(legit, impostor, config)
    sanity = sanity_check(legit, held_out, config)
    save_cache()

    out = root / "results" / f"trial_{args.trial}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "trial": args.trial, "seed": manifest["seed"], "legitimate": manifest["legitimate"],
        "n_impostor": len(impostor), "config": config, "records": records, "sanity": sanity,
    }, indent=2) + "\n")
    for record in records:
        print(f"{record['impostor']:7} matched={record['matched']!s:5} vs {record['matched_against']:7} "
              f"session ratios {record['session_ratios']}")
    for user, ratios in sanity.items():
        print(f"sanity {user}: held-out own-session ratios {ratios}")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
