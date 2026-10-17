#!/usr/bin/env python3
"""Density shape: a session's strokes combined into one shape. Every stroke starts at (0, 0) and keeps its direction
and its size (divided by the session's screen diagonal, so screens compare), is redrawn with 64 points evenly spaced
along its path, and every point is counted on a grid. The grid (how much stroke passes each cell) is the session's
shape; its contours are drawn. Sessions are compared with the Euclidean distance between square-root densities.
Profile = mean density of the enrolled sessions. Same session draw as 18 and 20. Writes runs/density_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
euclid_mod = import_module("20_euclidean_strokes")

GRID = 32           # cells per side
EXTENT = 0.5        # grid covers ±EXTENT screen diagonals around (0, 0); points beyond fall in the edge cells
SMOOTH = 1.0        # Gaussian blur in cells, so nearby strokes count as similar
POINTS = 64         # points per stroke, evenly spaced along its path (removes the logger's sampling rate)
MIN_STROKES = 10    # sessions with fewer strokes give no decision


def strokes(user: str, name: str, folder: str, config: dict) -> np.ndarray:
    """(m, POINTS, 2) strokes from (0, 0), direction and size kept, in screen diagonals."""
    df = cfg_mod.load_session(cfg_mod.ROOT / folder / user / name)
    if not len(df):
        return np.empty((0, POINTS, 2))
    screen = np.hypot(df["x"].max(), df["y"].max())
    out = []
    for chunk, _ in chunk_mod.segment(df, config):
        xy = chunk[:, :2] - chunk[0, :2]
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
        if arc[-1] > 0:
            grid = np.linspace(0, arc[-1], POINTS)
            out.append(np.column_stack([np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])]) / screen)
    return np.array(out).reshape(-1, POINTS, 2)


def density(paths: np.ndarray) -> np.ndarray | None:
    """Smoothed share of stroke points per cell (sums to 1); None when there are too few strokes."""
    if len(paths) < MIN_STROKES:
        return None
    pts = np.clip(paths.reshape(-1, 2), -EXTENT, EXTENT - 1e-9)
    h, _, _ = np.histogram2d(pts[:, 0], pts[:, 1], bins=GRID, range=[[-EXTENT, EXTENT]] * 2)
    h = gaussian_filter(h, SMOOTH)
    return h / h.sum()


def distance(d: np.ndarray | None, profile: np.ndarray) -> float:
    """Euclidean distance between square-root densities (Hellinger, up to a constant)."""
    return np.inf if d is None else float(np.linalg.norm(np.sqrt(d) - np.sqrt(profile)))


def run(config: dict, k: int) -> tuple[pd.DataFrame, dict]:
    state = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        load = lambda pairs: [strokes(u, n, f, config) for f, n in pairs]
        paths = load(pool[:k])
        enrolled = [d for d in map(density, paths) if d is not None]
        state[u] = {"profile": np.mean(enrolled, axis=0), "own": [density(p) for p in load(pool[-k:])],
                    "other": [density(p) for p in load(pool[k:2 * k])], "example": max(paths, key=len)}
    rows = []
    for p, st in state.items():
        tests = [(p, "genuine", d) for d in st["own"]] + \
                [(v, "impostor", d) for v, o in state.items() if v != p for d in o["other"]]
        rows += [{"profile": p, "user": v, "kind": kind, "score": distance(d, st["profile"])} for v, kind, d in tests]
    return pd.DataFrame(rows), state


def mass_level(d: np.ndarray, share: float) -> float:
    """Density value whose contour encloses `share` of the total."""
    s = np.sort(d.ravel())[::-1]
    return s[np.searchsorted(np.cumsum(s), share)]


def contour(ax, d: np.ndarray, shares=(0.5, 0.8), **style) -> None:
    c = (np.arange(GRID) + 0.5) / GRID * 2 * EXTENT - EXTENT
    levels = sorted(mass_level(d, s) for s in shares)
    ax.contour(c, c, d.T, levels=levels, **style)


def frame(ax) -> None:
    ax.plot(0, 0, "ko", ms=5); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.set_xlim(-EXTENT, EXTENT); ax.set_ylim(EXTENT, -EXTENT)   # screen coordinates: y grows down
    ax.tick_params(labelsize=7)


def plot_explained(state: dict, user: str, path_out, title: str) -> None:
    """strokes from (0, 0) -> grid of counts -> contours = the session's shape."""
    paths, d = state[user]["example"], density(state[user]["example"])
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.8))
    for p in paths:
        axes[0].plot(p[:, 0], p[:, 1], color="#4c78a8", alpha=0.25, lw=0.7)
    axes[0].set_title(f"1. {len(paths)} strokes of one {user} session, all from (0, 0)\n(direction and size kept)", fontsize=10)
    axes[1].imshow(d.T, extent=[-EXTENT, EXTENT, EXTENT, -EXTENT], cmap="Blues")
    axes[1].set_title(f"2. {GRID}×{GRID} grid: how much stroke passes each cell", fontsize=10)
    contour(axes[2], d, colors=["#4c78a8", "#1f3b63"], linewidths=[1.2, 2.2])
    axes[2].set_title("3. the shape: contours holding 80% (thin) and 50% (thick)\nof the session's stroke points", fontsize=10)
    for ax in axes:
        frame(ax)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(path_out, dpi=130); plt.close(fig)


def plot_users(state: dict, path_out, title: str) -> None:
    users = sorted(state, key=lambda u: int(u[4:]))
    cmap = plt.get_cmap("tab10")
    fig = plt.figure(figsize=(20, 10.5))
    grid = fig.add_gridspec(3, 5, width_ratios=[1.6, 1, 1, 1, 1])
    over = fig.add_subplot(grid[:, 0])
    for c, u in enumerate(users):
        contour(over, state[u]["profile"], shares=(0.5,), colors=[cmap(c)], linewidths=1.8)
        over.plot([], [], color=cmap(c), label=u)
    over.legend(fontsize=8, ncol=2, loc="lower left")
    over.set_title("Every user's profile shape (contour holding 50% of stroke points)", fontsize=10)
    frame(over)
    for c, u in enumerate(users):
        ax = fig.add_subplot(grid[c // 4, 1 + c % 4]) if c < 8 else fig.add_subplot(grid[2, 1 + c - 8])
        prof = state[u]["profile"]
        for v in users:
            for d in state[v]["other"] if v != u else []:
                if d is not None:
                    contour(ax, d, shares=(0.5,), colors=["#e45756"], linewidths=0.5, alpha=0.35)
        for d in state[u]["own"]:
            if d is not None:
                contour(ax, d, shares=(0.5,), colors=["#4c78a8"], linewidths=1.4)
        contour(ax, prof, shares=(0.5,), colors=["k"], linewidths=2.4)
        own = [distance(d, prof) for d in state[u]["own"] if d is not None]
        imp = [distance(d, prof) for v in users if v != u for d in state[v]["other"] if d is not None]
        mo, mi = (np.mean(own) if own else np.nan), np.mean(imp)
        ax.set_title(f"{u}: own {mo:.3f} vs impostor {mi:.3f}", fontsize=9, color="#2a7a2a" if mo < mi else "#b22222")
        frame(ax)
    fig.suptitle(title, fontsize=11); fig.tight_layout(); fig.savefig(path_out, dpi=120); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"density_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    results, scores = [], []
    for seed in args.seeds:
        config["seed"] = seed
        table, state = run(config, args.sessions)
        g = table[table.kind == "genuine"].score.to_numpy()
        i = table[table.kind == "impostor"].score.to_numpy()
        rate = euclid_mod.eer(g, i)
        results.append({"seed": seed, "eer": rate})
        scores.append(table.assign(seed=seed))
        print(f"seed {seed}: EER {rate:.1%} (median distance own {np.median(g):.3f}, impostor {np.median(i):.3f}, "
              f"no decision {np.isinf(table.score).sum()} of {len(table)})")
        if seed == args.seeds[0]:
            tag = f"{args.sessions} enrolled sessions, seed {seed}"
            plot_explained(state, "user29", out / "figures" / "density_explained.png", f"How a session becomes a shape ({tag})")
            plot_users(state, out / "figures" / "density_shapes.png",
                       f"Density shapes ({tag}). Black = profile, blue = the user's own new sessions, red = other "
                       "users' sessions; title = mean distance (green when own sessions are closer)")
            fig, ax = plt.subplots(figsize=(8, 4))
            fin = np.concatenate([g, i]); fin = fin[np.isfinite(fin)]
            bins = np.linspace(0, np.quantile(fin, 0.99), 40)
            ax.hist(i[np.isfinite(i)], bins, alpha=0.6, color="#e45756", density=True, label=f"impostor sessions ({len(i)})")
            ax.hist(g[np.isfinite(g)], bins, alpha=0.6, color="#4c78a8", density=True, label=f"own sessions ({len(g)})")
            ax.set_xlabel("Euclidean distance between the session's density shape and the profile")
            ax.set_title(f"{tag}: EER {rate:.1%} (own should sit left)", fontsize=9)
            ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / "scores.png", dpi=130); plt.close(fig)
    pd.concat(scores).to_csv(out / "scores.csv", index=False)
    summary = pd.DataFrame(results)
    summary.to_csv(out / "summary.csv", index=False)
    print(f"EER {summary.eer.mean():.1%} ± {summary.eer.std():.1%} over {len(summary)} draws")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
