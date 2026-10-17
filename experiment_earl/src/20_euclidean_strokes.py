#!/usr/bin/env python3
"""Pure Euclidean distance on stroke points: every normalized stroke (64 points from (0, 0)) is compared point by
point with the user's enrolled strokes of the same kind; a stroke's distance is its nearest enrolled stroke, a
session's score the median over its strokes. Same session draw as 18 and 19. Writes runs/euclidean_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
hull_mod = import_module("18_hull_profile")


def prepare(session, turn: bool) -> dict[int, np.ndarray]:
    """kind -> (m, 2n) flat point arrays, optionally turned so each stroke ends on the +x axis."""
    return {kind: (hull_mod.rotate(p) if turn and len(p) else p).reshape(len(p), 2 * p.shape[1]) for kind, p in session.paths.items()}


def nearest(query: dict, profile: dict) -> np.ndarray:
    """Per query stroke: RMS point distance to the closest profile stroke of the same kind."""
    out = []
    for kind, q in query.items():
        if len(q) and len(profile.get(kind, [])):
            n = q.shape[1] // 2
            out.append(cdist(q, profile[kind]).min(axis=1) / np.sqrt(n))
    return np.concatenate(out) if out else np.empty(0)


def eer(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """Equal error rate for distances (accept when distance <= t)."""
    rates = [((genuine > t).mean(), (impostor <= t).mean()) for t in np.unique(np.concatenate([genuine, impostor]))]
    frr, far = min(rates, key=lambda r: abs(r[0] - r[1]))
    return (frr + far) / 2


def run(config: dict, k: int, turn: bool) -> tuple[pd.DataFrame, dict]:
    rows, kept = [], {}
    sessions = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        load = lambda pairs: [prepare(match_mod.dataset_session(u, n, config, f), turn) for f, n in pairs]
        sessions[u] = (load(pool[:k]), load(pool[-k:]), load(pool[k:2 * k]))
    for p, (enrolled, own, _) in sessions.items():
        profile = {kind: np.concatenate([e[kind] for e in enrolled]) for kind in enrolled[0]}
        kept[p] = profile
        tests = [(p, "genuine", s) for s in own] + [(v, "impostor", s) for v, (_, _, o) in sessions.items() if v != p for s in o]
        for user, kind, s in tests:
            d = nearest(s, profile)
            rows.append({"profile": p, "user": user, "kind": kind, "strokes": len(d),
                         "score": float(np.median(d)) if len(d) >= 5 else np.inf})
    return pd.DataFrame(rows), {"profiles": kept, "sessions": sessions}


def plot_pairs(state: dict, user: str, other: str, path_out, title: str) -> None:
    """Left: the user's enrolled strokes. Middle/right: test strokes (own, impostor), each joined point by point to
    its nearest enrolled stroke; the grey connectors are the distances that get summed."""
    profile = state["profiles"][user][0]
    own = state["sessions"][user][1][0][0]
    imp = state["sessions"][other][2][0][0]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.6), sharex=True, sharey=True)
    for p in profile[:300]:
        axes[0].plot(p[0::2], p[1::2], color="#4c78a8", alpha=0.08, lw=0.7)
    axes[0].set_title(f"{user}: enrolled strokes ({len(profile)}), all from (0, 0)", fontsize=10)
    for ax, (label, q, color) in zip(axes[1:], [(f"{user}'s own new strokes", own, "#4c78a8"),
                                               (f"impostor {other}'s strokes", imp, "#e45756")]):
        d = cdist(q, profile)
        idx = d.argmin(axis=1)
        dist = d.min(axis=1) / np.sqrt(q.shape[1] // 2)
        for i in np.argsort(dist)[len(dist) // 2 - 3: len(dist) // 2 + 3]:   # six strokes around the median
            a, b = q[i].reshape(-1, 2), profile[idx[i]].reshape(-1, 2)
            for j in range(0, len(a), 3):
                ax.plot([a[j, 0], b[j, 0]], [a[j, 1], b[j, 1]], color="grey", lw=0.6, alpha=0.7)
            ax.plot(*b.T, color="k", lw=1.4)
            ax.plot(*a.T, color=color, lw=2)
        ax.set_title(f"{label}: 6 strokes around the median\nblack = nearest enrolled stroke, grey = point-to-point "
                     f"gaps; median distance {np.median(dist):.3f}", fontsize=10)
    for ax in axes:
        ax.plot(0, 0, "ko", ms=6); ax.set_aspect("equal"); ax.grid(alpha=0.2)
        ax.set_xlim(-1.1, 1.1); ax.set_ylim(-1.1, 1.1)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(path_out, dpi=120); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"euclidean_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    results, scores = [], []
    for turn in (False, True):
        for seed in args.seeds:
            config["seed"] = seed
            table, state = run(config, args.sessions, turn)
            g = table[table.kind == "genuine"].score.to_numpy()
            i = table[table.kind == "impostor"].score.to_numpy()
            rate = eer(g, i)
            results.append({"rotated": turn, "seed": seed, "eer": rate, "genuine_median": np.median(g),
                            "impostor_median": np.median(i)})
            scores.append(table.assign(rotated=turn, seed=seed))
            print(f"{'rotated' if turn else 'as drawn'} seed {seed}: EER {rate:.1%} "
                  f"(median distance own {np.median(g):.3f}, impostor {np.median(i):.3f})")
            if seed == args.seeds[0]:
                users = sorted(state["profiles"], key=lambda u: int(u[4:]))
                tag = "rotated" if turn else "as_drawn"
                for u in ("user20", "user29"):
                    other = users[(users.index(u) + 1) % len(users)]
                    plot_pairs(state, u, other, out / "figures" / f"pairs_{u}_{tag}.png",
                               f"Pure Euclidean distance on stroke points ({tag.replace('_', ' ')}, seed {seed})")
                fig, ax = plt.subplots(figsize=(8, 4))
                bins = np.linspace(0, np.quantile(np.concatenate([g, i])[np.isfinite(np.concatenate([g, i]))], 0.99), 40)
                ax.hist(i[np.isfinite(i)], bins, alpha=0.6, color="#e45756", density=True, label=f"impostor sessions ({len(i)})")
                ax.hist(g[np.isfinite(g)], bins, alpha=0.6, color="#4c78a8", density=True, label=f"own sessions ({len(g)})")
                ax.set_xlabel("session score: median distance of its strokes to the nearest enrolled stroke")
                ax.set_title(f"Pure Euclidean, {tag.replace('_', ' ')}, seed {seed}: EER {rate:.1%} (own should sit left)", fontsize=9)
                ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / f"scores_{tag}.png", dpi=130); plt.close(fig)
    pd.concat(scores).to_csv(out / "scores.csv", index=False)
    summary = pd.DataFrame(results).groupby("rotated")["eer"].agg(["mean", "std"])
    summary.round(4).to_csv(out / "summary.csv")
    print(summary.round(3).to_string())
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
