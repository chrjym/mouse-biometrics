#!/usr/bin/env python3
"""Short-signal turning profile with window decisions. Each movement (cut at pauses and clicks) keeps only its first
0.5 s; that piece is redrawn with 16 points evenly spaced along its path and described by the 14 signed turning angles
between its 15 segments (closed form; no position, size or direction). A piece scores the mean Euclidean distance to
its 5 nearest enrolled pieces, divided by the profile's own scale (the same score of each enrolled session against
the user's other enrolled sessions, so profiles with many or few pieces compare); a window of W consecutive pieces scores their mean. EER per window size W. Same session
draw as the other scripts. Writes runs/turning_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")

PIECE_S = 0.5            # keep the first this many seconds of each movement
POINTS = 16              # points per piece (a ~110 ms logger records only ~5 in 0.5 s)
MIN_RAW = 3              # raw points a piece needs
NEIGHBOURS = 5           # piece score = mean distance to this many nearest enrolled pieces
WINDOWS = (1, 5, 10, 20, 30)


def turning(xy: np.ndarray) -> np.ndarray | None:
    """Signed turning angles (radians) of a path redrawn with POINTS points along its arc length."""
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    if arc[-1] <= 0:
        return None
    grid = np.linspace(0, arc[-1], POINTS)
    p = np.column_stack([np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])])
    heading = np.arctan2(*np.diff(p, axis=0).T[::-1])
    return (np.diff(heading) + np.pi) % (2 * np.pi) - np.pi


def pieces(user: str, name: str, folder: str, config: dict) -> tuple[np.ndarray, list]:
    """(m, POINTS - 2) turning profiles of the first PIECE_S seconds of each movement, in time order, plus the paths."""
    df = cfg_mod.load_session(cfg_mod.ROOT / folder / user / name)
    out, paths = [], []
    for chunk, _ in chunk_mod.segment(df, {**config, "min_points": MIN_RAW}):
        piece = chunk[chunk[:, 2] - chunk[0, 2] <= PIECE_S]
        if len(piece) >= MIN_RAW and (a := turning(piece[:, :2])) is not None:
            out.append(a)
            paths.append(piece[:, :2] - piece[0, :2])
    return np.array(out).reshape(-1, POINTS - 2), paths


def piece_scores(query: np.ndarray, library: np.ndarray) -> np.ndarray:
    if not len(query):
        return np.empty(0)
    d = cdist(query, library)
    return np.sort(d, axis=1)[:, :NEIGHBOURS].mean(axis=1)


def windows(scores: np.ndarray, w: int) -> np.ndarray:
    """Mean score of consecutive, non-overlapping windows of w pieces."""
    n = len(scores) // w
    return scores[: n * w].reshape(n, w).mean(axis=1) if n else np.empty(0)


def eer(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """Equal error rate for scores where lower = more like the user (accept when score <= t)."""
    ts = np.unique(np.concatenate([genuine, impostor]))
    if len(ts) > 2000:
        ts = np.quantile(ts, np.linspace(0, 1, 2000))
    rates = [((genuine > t).mean(), (impostor <= t).mean()) for t in ts]
    frr, far = min(rates, key=lambda r: abs(r[0] - r[1]))
    return (frr + far) / 2


def run(config: dict, k: int) -> tuple[list[dict], dict]:
    data = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        load = lambda pairs: [pieces(u, n, f, config) for f, n in pairs]
        enrolled = load(pool[:k])
        parts = [a for a, _ in enrolled]
        # the profile's own scale: each enrolled session against the other enrolled sessions (registration data only)
        self_d = [piece_scores(a, np.concatenate([b for j, b in enumerate(parts) if j != i]))
                  for i, a in enumerate(parts) if len(a)]
        data[u] = {"library": np.concatenate(parts), "scale": float(np.median(np.concatenate(self_d))), "paths": [p for _, ps in enrolled for p in ps],
                   "own": [a for a, _ in load(pool[-k:])], "other": [a for a, _ in load(pool[k:2 * k])]}
    scored = {"genuine": [], "impostor": []}   # per tested session: piece scores in time order
    for p, d in data.items():
        scored["genuine"] += [piece_scores(s, d["library"]) / d["scale"] for s in d["own"]]
        scored["impostor"] += [piece_scores(s, d["library"]) / d["scale"] for v, o in data.items() if v != p
                               for s in o["other"]]
    rows = []
    for w in WINDOWS:
        g = np.concatenate([windows(s, w) for s in scored["genuine"]])
        i = np.concatenate([windows(s, w) for s in scored["impostor"]])
        rows.append({"window": w, "eer": eer(g, i), "genuine_windows": len(g), "impostor_windows": len(i)})
    return rows, {"data": data, "scored": scored}


def plot_explained(state: dict, user: str, path_out, title: str) -> None:
    """A 0.5 s piece, its 16 points, its turning angles; then the user's mean turning profile against everyone's."""
    d = state["data"][user]
    lengths = [np.hypot(*np.diff(p, axis=0).T).sum() for p in d["paths"]]
    idx = int(np.argsort(lengths)[int(0.7 * len(lengths))])
    path = d["paths"][idx]
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(path, axis=0).T))])
    grid = np.linspace(0, arc[-1], POINTS)
    p = np.column_stack([np.interp(grid, arc, path[:, 0]), np.interp(grid, arc, path[:, 1])])
    a = d["library"][idx]
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.3))
    axes[0].plot(*path.T, "o-", color="#bbbbbb", ms=4, label="recorded points")
    axes[0].plot(*p.T, "o-", color="#4c78a8", ms=5, lw=2, label=f"{POINTS} points along the path")
    for j in range(1, POINTS - 1):
        axes[0].annotate(f"{np.degrees(a[j - 1]):+.0f}°", p[j], fontsize=7, xytext=(4, 4), textcoords="offset points")
    axes[0].plot(0, 0, "ko"); axes[0].set_aspect("equal"); axes[0].invert_yaxis(); axes[0].legend(fontsize=8)
    axes[0].set_title(f"1. first {PIECE_S} s of one {user} movement (pixels);\nlabels = turn at each point", fontsize=10)
    axes[1].bar(range(1, POINTS - 1), np.degrees(a), color=["#54a24b" if x > 0 else "#e45756" for x in a])
    axes[1].axhline(0, color="k", lw=0.8)
    axes[1].set_xlabel("point along the piece"); axes[1].set_ylabel("turn (degrees)")
    axes[1].set_title(f"2. the piece as {POINTS - 2} numbers: its turning profile", fontsize=10)
    users = sorted(state["data"], key=lambda u: int(u[4:]))
    cmap = plt.get_cmap("tab10")
    x = np.arange(1, POINTS - 1)
    for c, u in enumerate(users):
        lib = np.degrees(state["data"][u]["library"])
        axes[2].plot(x, np.median(np.abs(lib), axis=0), color=cmap(c), lw=2.4 if u == user else 1.2,
                     label=u, alpha=1 if u == user else 0.6)
    axes[2].set_xlabel("point along the piece"); axes[2].set_ylabel("median |turn| (degrees)")
    axes[2].legend(fontsize=7, ncol=2)
    axes[2].set_title("3. every user's typical turning profile (enrolled pieces)", fontsize=10)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(path_out, dpi=130); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"turning_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in args.seeds:
        config["seed"] = seed
        result, state = run(config, args.sessions)
        rows += [{**r, "seed": seed} for r in result]
        print(f"seed {seed}: " + ", ".join(f"W={r['window']} {r['eer']:.1%}" for r in result))
        if seed == args.seeds[0]:
            plot_explained(state, "user29", out / "figures" / "turning_explained.png",
                           f"Turning profile of a 0.5 s piece ({args.sessions} enrolled sessions, seed {seed})")
            n = {u: len(d["library"]) for u, d in state["data"].items()}
            print("enrolled pieces per user:", n)
    table = pd.DataFrame(rows)
    table.to_csv(out / "results.csv", index=False)
    summary = table.groupby("window").agg(eer=("eer", "mean"), std=("eer", "std"),
                                          genuine_windows=("genuine_windows", "mean"),
                                          impostor_windows=("impostor_windows", "mean"))
    summary.round(4).to_csv(out / "summary.csv")
    print(summary.round(3).to_string())

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.errorbar(summary.index, summary.eer * 100, yerr=summary["std"] * 100, marker="o", capsize=4, color="#4c78a8")
    ax.axhline(50, color="k", ls="--", lw=1, label="chance (50%)")
    ax.axhline(43, color="#e45756", ls=":", lw=1.5, label="best shape-only so far (~43%)")
    ax.set_xlabel("window: consecutive 0.5 s pieces per decision"); ax.set_ylabel("EER %")
    ax.set_title(f"Turning profile, {args.sessions} enrolled sessions, mean ± std over {len(args.seeds)} draws", fontsize=10)
    ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / "eer_by_window.png", dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
