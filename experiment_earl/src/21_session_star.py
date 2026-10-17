#!/usr/bin/env python3
"""Direction star: a session's shape. Every move stroke starts at (0, 0) (direction kept), is sorted into 8 direction
groups by where it ends, and each group's median stroke (point by point) is one arm of the star. Sessions are compared
with the Euclidean (RMS) distance between their stars, arm by arm and point by point. Profile = star of all enrolled
strokes. Same session draw as 18 and 20. Writes runs/star_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
match_mod = import_module("04_match_shapes")
euclid_mod = import_module("20_euclidean_strokes")

ARMS = 8
MIN_STROKES = 3     # an arm needs at least this many strokes, otherwise it is left out
MIN_SHARED = 4      # two stars are compared only on arms both have; fewer than this -> no decision
NAMES = ["right", "down-right", "down", "down-left", "left", "up-left", "up", "up-right"]  # screen y grows down


def star(paths: np.ndarray) -> np.ndarray:
    """(ARMS, n, 2) median stroke per direction group; NaN where a group has too few strokes."""
    n = paths.shape[1] if paths.ndim == 3 else 64
    out = np.full((ARMS, n, 2), np.nan)
    if not len(paths):
        return out
    end = paths[:, -1]
    arm = np.round(np.arctan2(end[:, 1], end[:, 0]) / (2 * np.pi / ARMS)).astype(int) % ARMS
    for a in range(ARMS):
        if (arm == a).sum() >= MIN_STROKES:
            out[a] = np.median(paths[arm == a], axis=0)
    return out


def distance(s: np.ndarray, t: np.ndarray) -> float:
    """RMS point gap over the arms both stars have."""
    shared = ~np.isnan(s[:, 0, 0]) & ~np.isnan(t[:, 0, 0])
    if shared.sum() < MIN_SHARED:
        return np.inf
    return float(np.sqrt(np.mean(np.sum((s[shared] - t[shared]) ** 2, axis=-1))))


def run(config: dict, k: int) -> tuple[pd.DataFrame, dict]:
    moves = lambda u, pairs: [match_mod.dataset_session(u, n, config, f).paths[chunk_mod.MOVE] for f, n in pairs]
    state = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        enrolled = moves(u, pool[:k])
        state[u] = {"profile": star(np.concatenate(enrolled)),
                    "own": [star(p) for p in moves(u, pool[-k:])],
                    "other": [star(p) for p in moves(u, pool[k:2 * k])]}
    rows = []
    for p, st in state.items():
        tests = [(p, "genuine", s) for s in st["own"]] + \
                [(v, "impostor", s) for v, o in state.items() if v != p for s in o["other"]]
        for user, kind, s in tests:
            rows.append({"profile": p, "user": user, "kind": kind, "score": distance(s, st["profile"])})
    return pd.DataFrame(rows), state


def draw_star(ax, s: np.ndarray, **style) -> None:
    for arm in s:
        if not np.isnan(arm[0, 0]):
            ax.plot(arm[:, 0], arm[:, 1], **style)
            style.pop("label", None)


def plot_users(state: dict, path_out, title: str) -> None:
    """Left: every user's profile star on one origin. Grid: per user, profile star (black) with the user's own new
    session stars (blue) and the other users' session stars (red)."""
    users = sorted(state, key=lambda u: int(u[4:]))
    cmap = plt.get_cmap("tab10")
    fig = plt.figure(figsize=(20, 10.5))
    grid = fig.add_gridspec(3, 5, width_ratios=[1.6, 1, 1, 1, 1])
    over = fig.add_subplot(grid[:, 0])
    for c, u in enumerate(users):
        draw_star(over, state[u]["profile"], color=cmap(c), lw=1.8, label=u)
    over.set_title("Profile star of every user (4 enrolled sessions)", fontsize=10)
    over.legend(fontsize=8, ncol=2, loc="lower left")
    for c, u in enumerate(users):
        ax = fig.add_subplot(grid[c // 4, 1 + c % 4]) if c < 8 else fig.add_subplot(grid[2, 1 + c - 8])
        for v in users:
            if v != u:
                for s in state[v]["other"]:
                    draw_star(ax, s, color="#e45756", lw=0.5, alpha=0.25)
        for s in state[u]["own"]:
            draw_star(ax, s, color="#4c78a8", lw=1.3, alpha=0.9)
        draw_star(ax, state[u]["profile"], color="k", lw=2.2)
        own = np.mean([d for s in state[u]["own"] if np.isfinite(d := distance(s, state[u]["profile"]))] or [np.nan])
        imp = np.mean([d for v in users if v != u for s in state[v]["other"]
                       if np.isfinite(d := distance(s, state[u]["profile"]))])
        n_own = sum(np.isfinite(distance(s, state[u]["profile"])) for s in state[u]["own"])
        ax.set_title(f"{u}: own {own:.3f} ({n_own}/{len(state[u]['own'])} with a star) vs impostor {imp:.3f}", fontsize=9,
                     color="#2a7a2a" if own < imp else "#b22222")
        ax.tick_params(labelsize=7)
    for ax in fig.axes:
        ax.plot(0, 0, "ko", ms=5); ax.set_aspect("equal"); ax.grid(alpha=0.2)
        ax.set_xlim(-1.05, 1.05); ax.set_ylim(1.05, -1.05)    # screen coordinates: y grows down
    fig.suptitle(title, fontsize=11); fig.tight_layout(); fig.savefig(path_out, dpi=120); plt.close(fig)


def plot_one(state: dict, user: str, path_out, title: str) -> None:
    """How one session star is built and compared: arms labelled, own session vs profile with point gaps."""
    prof, own = state[user]["profile"], state[user]["own"][0]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.3))
    draw_star(axes[0], prof, color="k", lw=2.2)
    for a, arm in enumerate(prof):
        if not np.isnan(arm[0, 0]):
            axes[0].annotate(NAMES[a], arm[-1], fontsize=9, ha="center", va="center",
                             bbox={"boxstyle": "round", "fc": "white", "ec": "grey"})
    axes[0].set_title(f"{user}'s profile star: median stroke per direction", fontsize=10)
    shared = ~np.isnan(prof[:, 0, 0]) & ~np.isnan(own[:, 0, 0])
    for a in np.flatnonzero(shared):
        for j in range(0, prof.shape[1], 3):
            axes[1].plot([prof[a, j, 0], own[a, j, 0]], [prof[a, j, 1], own[a, j, 1]], color="grey", lw=0.6)
    draw_star(axes[1], prof, color="k", lw=2.2, label="profile star")
    draw_star(axes[1], own, color="#4c78a8", lw=2, label="one new session's star")
    axes[1].legend(fontsize=9, loc="lower left")
    axes[1].set_title(f"Euclidean distance = RMS of the grey gaps = {distance(own, prof):.3f}", fontsize=10)
    for ax in axes:
        ax.plot(0, 0, "ko", ms=6); ax.set_aspect("equal"); ax.grid(alpha=0.2)
        ax.set_xlim(-1.05, 1.05); ax.set_ylim(1.05, -1.05)
    fig.suptitle(title); fig.tight_layout(); fig.savefig(path_out, dpi=130); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"star_{args.sessions}"
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
            plot_users(state, out / "figures" / "stars.png",
                       f"Direction stars ({tag}). Black = profile star, blue = the user's own new sessions, "
                       "red = other users' sessions; title = mean distance (green when own sessions are closer)")
            plot_one(state, "user29", out / "figures" / "star_explained.png", f"How a session star is compared ({tag})")
            fig, ax = plt.subplots(figsize=(8, 4))
            fin = np.concatenate([g, i]); fin = fin[np.isfinite(fin)]
            bins = np.linspace(0, np.quantile(fin, 0.99), 40)
            ax.hist(i[np.isfinite(i)], bins, alpha=0.6, color="#e45756", density=True, label=f"impostor sessions ({len(i)})")
            ax.hist(g[np.isfinite(g)], bins, alpha=0.6, color="#4c78a8", density=True, label=f"own sessions ({len(g)})")
            ax.set_xlabel("Euclidean distance between the session star and the profile star")
            ax.set_title(f"{tag}: EER {rate:.1%} (own should sit left)", fontsize=9)
            ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / "scores.png", dpi=130); plt.close(fig)
    pd.concat(scores).to_csv(out / "scores.csv", index=False)
    summary = pd.DataFrame(results)
    summary.to_csv(out / "summary.csv", index=False)
    print(f"EER {summary.eer.mean():.1%} ± {summary.eer.std():.1%} over {len(summary)} draws")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
