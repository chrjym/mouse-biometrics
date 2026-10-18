#!/usr/bin/env python3
"""Tube shape: alike strokes combined into one shape per group. Strokes keep direction and size (divided by the
session's screen diagonal), are redrawn with 64 points along the path, lined up at their start (or end) at (0, 0) and
grouped by direction (8) and length (short / medium / long). Per group, the mean path is the spine and the spread
around it at each point is the width: spine + width = the tube. A new stroke scores the mean of its point gaps to the
spine divided by the tube width; a session scores the median over its strokes. Same session draw as the other
scripts: profile = first k sessions, own test = last k, impostor test = sessions k..2k of every other user.
Writes runs/tube_<anchor>_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")

POINTS = 64          # points per stroke, evenly spaced along its path
DIRECTIONS = 8       # direction groups by the chord's angle
LENGTHS = ("short", "medium", "long")
MIN_TUBE = 5         # strokes needed to build a tube
MIN_SCORED = 5       # scored strokes needed for a session decision
FLOOR = 0.003        # smallest tube width (screen diagonals), so a tight spot cannot divide by ~0
NAMES = ["right", "down-right", "down", "down-left", "left", "up-left", "up", "up-right"]  # screen y grows down


def strokes(user: str, name: str, folder: str, config: dict) -> np.ndarray:
    """(m, POINTS, 2) strokes from their start, direction and size kept, in screen diagonals."""
    df = cfg_mod.load_session(cfg_mod.ROOT / folder / user / name)
    if not len(df):
        return np.empty((0, POINTS, 2))
    screen = np.hypot(df["x"].max(), df["y"].max())
    out = []
    for chunk, _ in chunk_mod.segment(df, config):
        xy = chunk[:, :2] - chunk[0, :2]
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
        if arc[-1] > 0 and np.hypot(*xy[-1]) > 0:
            grid = np.linspace(0, arc[-1], POINTS)
            out.append(np.column_stack([np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])]) / screen)
    return np.array(out).reshape(-1, POINTS, 2)


def groups(paths: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    """Group id per stroke: direction * len(LENGTHS) + length class."""
    end = paths[:, -1]
    direction = np.round(np.arctan2(end[:, 1], end[:, 0]) / (2 * np.pi / DIRECTIONS)).astype(int) % DIRECTIONS
    length = np.searchsorted(cuts, np.hypot(end[:, 0], end[:, 1]))
    return direction * len(LENGTHS) + length


def anchored(paths: np.ndarray, anchor: str) -> np.ndarray:
    """Line strokes up at their start (already) or at their end."""
    return paths - paths[:, -1:] if anchor == "end" else paths


def tubes(paths: np.ndarray, gid: np.ndarray) -> dict[int, tuple[np.ndarray, np.ndarray, int]]:
    """Per group with enough strokes: (spine (POINTS, 2), width (POINTS,), stroke count)."""
    out = {}
    for g in np.unique(gid):
        p = paths[gid == g]
        if len(p) >= MIN_TUBE:
            spine = p.mean(axis=0)
            width = np.maximum(np.sqrt(np.mean(np.sum((p - spine) ** 2, axis=-1), axis=0)), FLOOR)
            out[g] = (spine, width, len(p))
    return out


def stroke_scores(paths: np.ndarray, gid: np.ndarray, profile: dict) -> np.ndarray:
    """Per stroke with a tube in its group: mean over points of gap to the spine / tube width."""
    out = []
    for p, g in zip(paths, gid):
        if g in profile:
            spine, width, _ = profile[g]
            out.append(np.mean(np.hypot(*(p - spine).T) / width))
    return np.array(out)


def session_score(paths: np.ndarray, profile: dict, cuts: np.ndarray, anchor: str) -> float:
    s = stroke_scores(anchored(paths, anchor), groups(paths, cuts), profile) if len(paths) else np.empty(0)
    return float(np.median(s)) if len(s) >= MIN_SCORED else np.inf


def eer(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """Equal error rate for scores where lower = more like the user (accept when score <= t)."""
    rates = [((genuine > t).mean(), (impostor <= t).mean()) for t in np.unique(np.concatenate([genuine, impostor]))]
    frr, far = min(rates, key=lambda r: abs(r[0] - r[1]))
    return (frr + far) / 2


def run(config: dict, k: int, anchor: str) -> tuple[pd.DataFrame, dict]:
    data = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        load = lambda pairs: [strokes(u, n, f, config) for f, n in pairs]
        data[u] = {"enrolled": np.concatenate(load(pool[:k])), "own": load(pool[-k:]), "other": load(pool[k:2 * k])}
    # length classes: terciles of every enrolled stroke's chord (no labels used)
    chords = np.concatenate([np.hypot(*d["enrolled"][:, -1].T) for d in data.values()])
    cuts = np.quantile(chords, [1 / 3, 2 / 3])
    for d in data.values():
        d["tubes"] = tubes(anchored(d["enrolled"], anchor), groups(d["enrolled"], cuts))
    rows = []
    for p, d in data.items():
        tests = [(p, "genuine", s) for s in d["own"]] + \
                [(v, "impostor", s) for v, o in data.items() if v != p for s in o["other"]]
        rows += [{"profile": p, "user": v, "kind": kind, "score": session_score(s, d["tubes"], cuts, anchor)}
                 for v, kind, s in tests]
    return pd.DataFrame(rows), {"data": data, "cuts": cuts}


def band(spine: np.ndarray, width: np.ndarray) -> np.ndarray:
    """Polygon of spine ± width along the spine's normal."""
    tangent = np.gradient(spine, axis=0)
    tangent /= np.maximum(np.hypot(*tangent.T), 1e-12)[:, None]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    return np.vstack([spine + normal * width[:, None], (spine - normal * width[:, None])[::-1]])


def frame(ax, lim: float) -> None:
    ax.plot(0, 0, "ko", ms=5); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    ax.set_xlim(-lim, lim); ax.set_ylim(lim, -lim)   # screen coordinates: y grows down
    ax.tick_params(labelsize=7)


def draw_tubes(ax, profile: dict, length: int, color, label=None) -> None:
    for g, (spine, width, _) in profile.items():
        if g % len(LENGTHS) == length:
            poly = band(spine, width)
            ax.fill(*poly.T, color=color, alpha=0.18, lw=0)
            ax.plot(*spine.T, color=color, lw=1.8, label=label)
            label = None


def plot_explained(state: dict, user: str, anchor: str, path_out, title: str) -> None:
    """One group of one user: the alike strokes, the spine, the tube; then all 8 directions = the user's shape."""
    d, cuts = state["data"][user], state["cuts"]
    paths, gid = anchored(d["enrolled"], anchor), groups(d["enrolled"], cuts)
    medium = {g: t for g, t in d["tubes"].items() if g % len(LENGTHS) == 1}
    g = max(medium, key=lambda x: medium[x][2])
    spine, width, n = medium[g]
    lim = 1.15 * np.abs(paths[gid % len(LENGTHS) == 1]).max()
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.8))
    for p in paths[gid == g]:
        axes[0].plot(*p.T, color="#4c78a8", alpha=0.35, lw=0.8)
    axes[0].set_title(f"1. {n} alike strokes: direction '{NAMES[g // len(LENGTHS)]}', medium length,\n"
                      f"lined up at their {anchor} (0, 0)", fontsize=10)
    poly = band(spine, width)
    axes[1].fill(*poly.T, color="#4c78a8", alpha=0.25, label="tube: ± spread")
    axes[1].plot(*spine.T, color="k", lw=2.2, label="spine: mean path")
    axes[1].legend(fontsize=8, loc="lower left")
    axes[1].set_title("2. spine (mean of the 64 points) and width (spread of the\nstrokes around each point)", fontsize=10)
    draw_tubes(axes[2], d["tubes"], 1, "#4c78a8")
    axes[2].set_title(f"3. {user}'s shape: one tube per direction (medium strokes)", fontsize=10)
    for ax in axes:
        frame(ax, lim)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(path_out, dpi=130); plt.close(fig)


def plot_users(state: dict, path_out, title: str) -> None:
    """Every user's medium-length tubes: on one origin (left) and one panel per user."""
    data = state["data"]
    users = sorted(data, key=lambda u: int(u[4:]))
    cmap = plt.get_cmap("tab10")
    lim = 1.15 * max(np.abs(s).max() for d in data.values() for g, (s, _, _) in d["tubes"].items() if g % 3 == 1)
    fig = plt.figure(figsize=(20, 10.5))
    grid = fig.add_gridspec(3, 5, width_ratios=[1.6, 1, 1, 1, 1])
    over = fig.add_subplot(grid[:, 0])
    for c, u in enumerate(users):
        draw_tubes(over, data[u]["tubes"], 1, cmap(c), label=u)
    over.legend(fontsize=8, ncol=2, loc="lower left")
    over.set_title("Every user's tubes (medium strokes) on one origin", fontsize=10)
    frame(over, lim)
    for c, u in enumerate(users):
        ax = fig.add_subplot(grid[c // 4, 1 + c % 4]) if c < 8 else fig.add_subplot(grid[2, 1 + c - 8])
        draw_tubes(ax, data[u]["tubes"], 1, cmap(c))
        ax.set_title(f"{u} ({len(data[u]['enrolled'])} enrolled strokes)", fontsize=9)
        frame(ax, lim)
    fig.suptitle(title, fontsize=11); fig.tight_layout(); fig.savefig(path_out, dpi=120); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--anchor", choices=["start", "end"], default="start", help="line strokes up at their start or end")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"tube_{args.anchor}_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    results, scores = [], []
    for seed in args.seeds:
        config["seed"] = seed
        table, state = run(config, args.sessions, args.anchor)
        g = table[table.kind == "genuine"].score.to_numpy()
        i = table[table.kind == "impostor"].score.to_numpy()
        rate = eer(g, i)
        results.append({"seed": seed, "eer": rate})
        scores.append(table.assign(seed=seed))
        print(f"seed {seed}: EER {rate:.1%} (median score own {np.median(g):.2f}, impostor {np.median(i):.2f}, "
              f"no decision {np.isinf(table.score).sum()} of {len(table)})")
        if seed == args.seeds[0]:
            tag = f"lined up at {args.anchor}, {args.sessions} enrolled sessions, seed {seed}"
            plot_explained(state, "user29", args.anchor, out / "figures" / "tube_explained.png", f"How alike strokes become a tube ({tag})")
            plot_users(state, out / "figures" / "tubes.png", f"Tube shapes per user ({tag})")
            fig, ax = plt.subplots(figsize=(8, 4))
            fin = np.concatenate([g, i]); fin = fin[np.isfinite(fin)]
            bins = np.linspace(0, np.quantile(fin, 0.99), 40)
            ax.hist(i[np.isfinite(i)], bins, alpha=0.6, color="#e45756", density=True, label=f"impostor sessions ({len(i)})")
            ax.hist(g[np.isfinite(g)], bins, alpha=0.6, color="#4c78a8", density=True, label=f"own sessions ({len(g)})")
            ax.set_xlabel("session score: median stroke gap to the spine, in tube widths")
            ax.set_title(f"{tag}: EER {rate:.1%} (own should sit left)", fontsize=9)
            ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / "scores.png", dpi=130); plt.close(fig)
    pd.concat(scores).to_csv(out / "scores.csv", index=False)
    summary = pd.DataFrame(results)
    summary.to_csv(out / "summary.csv", index=False)
    print(f"EER {summary.eer.mean():.1%} ± {summary.eer.std():.1%} over {len(summary)} draws")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
