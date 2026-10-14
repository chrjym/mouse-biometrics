#!/usr/bin/env python3
"""Draw the impostor strokes that matched each legitimate user's strokes in the session progression notebook, one figure per user and session step."""

import argparse
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit, prange

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
match_mod = import_module("04_match_shapes")

KIND_NAMES = {chunk_mod.MOVE: "move", chunk_mod.DRAG: "drag"}
_dtw_within = match_mod._dtw_within


@njit(parallel=True, cache=True)
def first_match(queries, library, band, cap):
    """Per query path: index of the first library path within DTW cost `cap`, or -1 (same search as has_match)."""
    n = queries.shape[1]
    found = np.full(queries.shape[0], -1, dtype=np.int64)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            if _dtw_within(queries[q], library[k], band, cap, prev, cur):
                found[q] = k
                break
    return found


@njit(cache=True)
def dtw_cost(a, b, band):
    """Banded DTW cost between paths a and b (the value has_match compares with dtw_tolerance * resample_n)."""
    n = a.shape[0]
    cost = np.full((n + 1, n + 1), np.inf)
    cost[0, 0] = 0.0
    for i in range(n):
        for j in range(max(0, i - band), min(n - 1, i + band) + 1):
            d = np.sqrt((a[i, 0] - b[j, 0]) ** 2 + (a[i, 1] - b[j, 1]) ** 2)
            cost[i + 1, j + 1] = d + min(cost[i, j], cost[i, j + 1], cost[i + 1, j])
    return cost[n, n]


def draw_users(config: dict, seed: int) -> tuple[list[str], list[str], dict[str, list[tuple[str, str]]]]:
    """The notebook's draw, made once from `seed` and fixed for the whole run: legitimate users in draw order, sorted
    impostors, each user's shuffled session pool."""
    users = cfg_mod.list_users(config)
    rng = random.Random(seed)
    legit = rng.sample(users, config["n_legitimate"])
    impostor = sorted(rng.sample([u for u in users if u not in legit], config["n_impostor"]))
    return legit, impostor, {user: cfg_mod.session_pool(config, user, seed) for user in legit + impostor}


def step_matches(profile: str, impostor: list[str], order: dict, k: int, config: dict, pairs: dict) -> list[dict]:
    """Every impostor stroke (first k sessions) with a matching stroke in the profile's first k sessions."""
    n = config["resample_n"]
    band, cap = int(round(config["dtw_band"] * n)), config["dtw_tolerance"] * n
    library = [match_mod.dataset_session(profile, name, config, folder) for folder, name in order[profile][:k]]
    rows = []
    for user in impostor:
        for (folder, name) in order[user][:k]:
            query = match_mod.dataset_session(user, name, config, folder)
            for kind, paths in query.paths.items():
                best = np.full(len(paths), -1)
                source = np.full(len(paths), -1)
                for j, lib in enumerate(library):
                    key = (query.key, lib.key, kind)
                    if key not in pairs:
                        pairs[key] = first_match(paths, lib.paths[kind], band, cap) if len(lib.paths[kind]) and len(paths) \
                            else np.full(len(paths), -1)
                    new = (best < 0) & (pairs[key] >= 0)
                    best[new], source[new] = pairs[key][new], j
                for q in np.flatnonzero(best >= 0):
                    lib = library[source[q]]
                    rows.append({"profile": profile, "sessions": k, "impostor": user, "impostor_session": name,
                                 "kind": KIND_NAMES[kind], "chunk": int(q), "profile_session": lib.key.split("/")[-1],
                                 "profile_chunk": int(best[q]),
                                 "cost_per_point": dtw_cost(paths[q], lib.paths[kind][best[q]], band) / n,
                                 "query": paths[q], "match": lib.paths[kind][best[q]]})
    return rows


def session_verdicts(rows: list[dict], impostor: list[str], order: dict, k: int, config: dict) -> list[str]:
    """Per impostor: matched strokes and sessions at the notebook's matching rules (the bar graph's count)."""
    lines = []
    for user in impostor:
        ratios, strokes, matched = [], 0, 0
        for folder, name in order[user][:k]:
            session = match_mod.dataset_session(user, name, config, folder)
            hits = sum(r["impostor"] == user and r["impostor_session"] == name for r in rows)
            ratios.append(hits / max(session.n_chunks, 1))
            strokes += session.n_chunks
            matched += hits
        hit_sessions = sum(r >= config["match_shape_ratio"] for r in ratios)
        verdict = "MATCHED" if hit_sessions / len(ratios) >= config["match_session_ratio"] else "not matched"
        lines.append(f"{user}: {matched:,}/{strokes:,} strokes match, {hit_sessions}/{len(ratios)} sessions "
                     f"≥ {config['match_shape_ratio']:.0%} → {verdict}")
    return lines


def plot_step(rows: list[dict], verdicts: list[str], profile: str, k: int, limit: int, path) -> int:
    shown = sorted(random.Random(f"{profile}-{k}").sample(rows, min(limit, len(rows))),
                   key=lambda r: (r["impostor"], r["impostor_session"], r["kind"], r["chunk"]))
    cols = min(6, len(shown))
    n_rows = -(-len(shown) // cols)
    header = 0.2 * (len(verdicts) + 2)  # inches for the title lines
    fig, axes = plt.subplots(n_rows, cols, figsize=(cols * 1.9, n_rows * 2.1 + header), squeeze=False)
    for ax, r in zip(axes.flat, shown):
        ax.plot(r["match"][:, 0], r["match"][:, 1], color="tab:blue", linewidth=1.6, label=profile)
        ax.plot(r["query"][:, 0], r["query"][:, 1], color="tab:red", linewidth=1.0, linestyle="--", label="impostor")
        ax.plot(0, 0, "o", color="tab:green", markersize=3)
        ax.set_aspect("equal", adjustable="datalim")
        ax.invert_yaxis()
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"{r['impostor']} {r['impostor_session'][-6:]} {r['kind']} #{r['chunk']}\n"
                     f"→ {r['profile_session'][-6:]} #{r['profile_chunk']}, cost {r['cost_per_point']:.3f}",
                     fontsize=6.5)
    for ax in axes.flat[len(shown):]:
        ax.axis("off")
    fig.suptitle(f"{profile}, {k} sessions per user: {len(shown)} of {len(rows):,} matched impostor strokes "
                 f"(red dashed) on {profile}'s stroke (blue), green = start\n" + "\n".join(verdicts), fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 1 - header / fig.get_figheight()))
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return len(shown)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="legitimate users to draw (repeatable; default all)")
    parser.add_argument("--sessions", type=int, action="append", help="session steps to draw (repeatable; default all)")
    parser.add_argument("--max", type=int, default=36, help="matched pairs per figure (random sample)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    legit, impostor, order = draw_users(config, config["seed"])
    profiles = [u for u in legit if not args.user or u in args.user]
    if not profiles:
        raise SystemExit(f"None of {args.user} is legitimate in this run; legitimate users: {', '.join(legit)}")
    steps = [k for k in range(1, config["sessions_per_user"] + 1) if not args.sessions or k in args.sessions]
    print(f"Seed {config['seed']}: legitimate {', '.join(legit)}; "
          f"impostors {', '.join(impostor)}; session steps {steps}")

    out = run / "figures" / "matches"
    out.mkdir(parents=True, exist_ok=True)
    pairs, table = {}, []
    for profile in profiles:
        for k in steps:
            rows = step_matches(profile, impostor, order, k, config, pairs)
            verdicts = session_verdicts(rows, impostor, order, k, config)
            table += [{c: v for c, v in r.items() if c not in ("query", "match")} for r in rows]
            shown = plot_step(rows, verdicts, profile, k, args.max, out / f"{profile}_sessions{k}.png") if rows else 0
            print(f"{profile} {k} sessions: {len(rows):,} matched strokes, {shown} drawn | " + " | ".join(verdicts),
                  flush=True)

    results = run / "results"
    results.mkdir(exist_ok=True)
    pd.DataFrame(table).round(4).to_csv(results / "matches.csv", index=False)
    print(f"Output: {out}, {results / 'matches.csv'}")


if __name__ == "__main__":
    main()
