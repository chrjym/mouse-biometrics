#!/usr/bin/env python3
"""Convex hull profile per user: every stroke starts at (0, 0) and is turned so it ends on the +x axis; a user's
repeated strokes (DTW match in another own session within `sensitivity`) are bounded by a full and a core hull.
Writes runs/hull_<sensitivity>_<sessions>/ with figures, hulls.json and scores.csv."""

import argparse
import json
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath
from scipy.spatial import ConvexHull

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
match_mod = import_module("04_match_shapes")

KINDS = {chunk_mod.MOVE: "move", chunk_mod.DRAG: "drag"}


def rotate(paths: np.ndarray) -> np.ndarray:
    """Turn each path about (0, 0) so its end point lies on the +x axis; paths that end at the origin stay as they are."""
    end = paths[:, -1]
    angle = np.where(np.hypot(end[:, 0], end[:, 1]) > 1e-9, np.arctan2(end[:, 1], end[:, 0]), 0.0)
    c, s = np.cos(-angle)[:, None], np.sin(-angle)[:, None]
    x, y = paths[..., 0], paths[..., 1]
    return np.stack([c * x - s * y, s * x + c * y], axis=-1)


def repeated(sessions: list, kind: int, config: dict) -> np.ndarray:
    """Paths of `kind` that match (DTW within sensitivity) a path in another of the same user's sessions."""
    keep = []
    for i, s in enumerate(sessions):
        found = np.zeros(len(s.paths[kind]), dtype=bool)
        for j, other in enumerate(sessions):
            if i != j:
                found |= match_mod.pair_matches(s, other, config)[kind]
        keep.append(s.paths[kind][found])
    return np.concatenate(keep) if keep else np.empty((0, config["resample_n"], 2))


def hulls(paths: np.ndarray, core_share: float) -> dict | None:
    """Full hull of every point, and core hull of the points nearest the median path (per resample index)."""
    if len(paths) < 3:
        return None
    points = paths.reshape(-1, 2)
    dist = np.hypot(*(paths - np.median(paths, axis=0)).transpose(2, 0, 1)).ravel()
    core = points[dist <= np.quantile(dist, core_share)]
    full_hull, core_hull = ConvexHull(points), ConvexHull(core)
    return {"full": points[full_hull.vertices], "core": core[core_hull.vertices],
            "full_area": full_hull.volume, "core_area": core_hull.volume,
            "median": np.median(paths, axis=0), "n_paths": len(paths)}


def inside_share(paths: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Per path: share of its points inside `polygon`."""
    if not len(paths):
        return np.empty(0)
    inside = MplPath(polygon).contains_points(paths.reshape(-1, 2), radius=1e-9)
    return inside.reshape(len(paths), -1).mean(axis=1)


def session_score(session, profile: dict, config: dict, turn: bool) -> float:
    """Mean core-hull inside share over the session's strokes (move and drag each against their own hull)."""
    shares = []
    for kind, paths in session.paths.items():
        if profile.get(kind) is not None and len(paths):
            shares.append(inside_share(rotate(paths) if turn else paths, profile[kind]["core"]))
    return float(np.concatenate(shares).mean()) if shares else 0.0


def eer(genuine: np.ndarray, impostor: np.ndarray) -> tuple[float, float]:
    """Equal error rate and its threshold (a session is accepted when its score >= threshold)."""
    rates = [((genuine < t).mean(), (impostor >= t).mean(), t) for t in np.unique(np.concatenate([genuine, impostor]))]
    frr, far, t = min(rates, key=lambda r: abs(r[0] - r[1]))
    return (frr + far) / 2, t


def plot_profile(user: str, prof: dict, test: dict, out, title: str) -> None:
    """Enrolled strokes, full and core hull at (0, 0); right: the user's own test strokes and one impostor's."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharex=True, sharey=True)
    for ax, (label, paths, color) in zip(axes, [("enrolled (repeated) strokes", prof["paths"], "#4c78a8"),
                                                ("test: own (blue) vs impostor (red)", None, None)]):
        if paths is not None:
            for p in paths[:400]:
                ax.plot(p[:, 0], p[:, 1], color=color, alpha=0.08, lw=0.7)
        else:
            for p in test["own"][:150]:
                ax.plot(p[:, 0], p[:, 1], color="#4c78a8", alpha=0.15, lw=0.7)
            for p in test["impostor"][:150]:
                ax.plot(p[:, 0], p[:, 1], color="#e45756", alpha=0.15, lw=0.7)
        for key, style in (("full", "--"), ("core", "-")):
            poly = np.vstack([prof[key], prof[key][:1]])
            ax.plot(poly[:, 0], poly[:, 1], "k" + style, lw=1.6, label=f"{key} hull")
        ax.plot(*prof["median"].T, color="#f58518", lw=2, label="median path")
        ax.plot(0, 0, "ko", ms=6)
        ax.axhline(0, color="grey", lw=0.4); ax.axvline(0, color="grey", lw=0.4)
        ax.set_aspect("equal"); ax.set_title(label, fontsize=10)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def plot_nested(profiles: dict, kind: int, out, title: str) -> None:
    """Every user's core hull on one origin, to see how the profiles nest or overlap."""
    fig, ax = plt.subplots(figsize=(7, 6))
    cmap = plt.get_cmap("tab10")
    for i, (user, prof) in enumerate(profiles.items()):
        if prof.get(kind) is None:
            continue
        poly = np.vstack([prof[kind]["core"], prof[kind]["core"][:1]])
        ax.fill(poly[:, 0], poly[:, 1], color=cmap(i), alpha=0.12)
        ax.plot(poly[:, 0], poly[:, 1], color=cmap(i), lw=1.5, label=f"{user} ({prof[kind]['core_area']:.2f})")
    ax.plot(0, 0, "ko", ms=6); ax.axhline(0, color="grey", lw=0.4); ax.axvline(0, color="grey", lw=0.4)
    ax.set_aspect("equal"); ax.legend(fontsize=8, title="core hull (area)", loc="center left", bbox_to_anchor=(1, 0.5))
    ax.set_title(title); fig.tight_layout(); fig.savefig(out, dpi=130); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sensitivity", type=float, default=0.04)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--core", type=float, default=0.9, help="share of points nearest the median path kept for the core hull")
    parser.add_argument("--no-rotate", action="store_true", help="keep each stroke's direction (skip the turn to +x)")
    args = parser.parse_args()

    config = cfg_mod.load_config(sensitivity=args.sensitivity, sessions_per_user=args.sessions)
    turn, k = not args.no_rotate, args.sessions
    out = cfg_mod.RUNS / f"hull_{args.sensitivity}_{k}{'' if turn else '_norotate'}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    match_mod.load_cache()

    users = cfg_mod.list_users(config)
    pools = {u: cfg_mod.session_pool(config, u, config["seed"]) for u in users}
    load = lambda u, pairs: [match_mod.dataset_session(u, n, config, f) for f, n in pairs]
    enrolled = {u: load(u, pools[u][:k]) for u in users}
    genuine_test = {u: load(u, pools[u][-k:]) for u in users}   # never in a profile
    impostor_test = {u: load(u, pools[u][k:2 * k]) for u in users}  # never in their own profile either

    profiles, saved = {}, {}
    for u in users:
        profiles[u] = {}
        for kind in KINDS:
            paths = repeated(enrolled[u], kind, config)
            paths = rotate(paths) if turn else paths
            h = hulls(paths, args.core)
            if h:
                h["paths"] = paths
            profiles[u][kind] = h
        saved[u] = {KINDS[kd]: None if h is None else {"n_paths": h["n_paths"], "full_area": round(h["full_area"], 4),
                    "core_area": round(h["core_area"], 4), "full": h["full"].round(4).tolist(),
                    "core": h["core"].round(4).tolist()} for kd, h in profiles[u].items()}
        print(f"{u}: " + ", ".join(f"{KINDS[kd]} {h['n_paths'] if h else 0} strokes, core area "
                                   f"{h['core_area']:.3f}" if h else f"{KINDS[kd]} too few" for kd, h in profiles[u].items()))
    match_mod.save_cache()
    (out / "hulls.json").write_text(json.dumps({"sensitivity": args.sensitivity, "sessions": k, "core": args.core,
                                                "rotate": turn, "users": saved}, indent=1))

    rows = []
    for p in users:
        for v in users:
            for s in (genuine_test[v] if v == p else impostor_test[v]):
                rows.append({"profile": p, "user": v, "kind": "genuine" if v == p else "impostor",
                             "session": s.key, "score": session_score(s, profiles[p], config, turn)})
    scores = pd.DataFrame(rows)
    scores.to_csv(out / "scores.csv", index=False)
    g, i = scores[scores.kind == "genuine"].score.to_numpy(), scores[scores.kind == "impostor"].score.to_numpy()
    rate, threshold = eer(g, i)
    tag = f"sensitivity {args.sensitivity}, {k} sessions, core {args.core:.0%}, {'rotated' if turn else 'not rotated'}"
    print(f"EER {rate:.1%} at threshold {threshold:.3f}  (genuine mean {g.mean():.3f}, impostor mean {i.mean():.3f})")

    rng = np.random.default_rng(config["seed"])
    for u in users:
        prof = profiles[u][chunk_mod.MOVE]
        if prof is None:
            continue
        other = users[(users.index(u) + 1) % len(users)]
        cat = lambda ss: np.concatenate([x.paths[chunk_mod.MOVE] for x in ss])
        own, imp = cat(genuine_test[u]), cat(impostor_test[other])
        test = {"own": rotate(own) if turn else own, "impostor": rotate(imp) if turn else imp}
        test = {key: v[rng.permutation(len(v))] for key, v in test.items()}
        plot_profile(u, prof, test, out / "figures" / f"profile_{u}.png", f"{u} move-stroke hull vs {other} ({tag})")
    for kind, name in KINDS.items():
        plot_nested(profiles, kind, out / "figures" / f"nested_{name}.png", f"Core hulls of all users, {name} ({tag})")

    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(0, 1, 41)
    ax.hist(i, bins, alpha=0.6, color="#e45756", label=f"impostor ({len(i)})", density=True)
    ax.hist(g, bins, alpha=0.6, color="#4c78a8", label=f"genuine ({len(g)})", density=True)
    ax.axvline(threshold, color="k", ls="--", label=f"EER {rate:.1%}")
    ax.set_xlabel("session score: share of stroke points inside the core hull"); ax.legend()
    ax.set_title(tag, fontsize=10); fig.tight_layout(); fig.savefig(out / "figures" / "scores.png", dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
