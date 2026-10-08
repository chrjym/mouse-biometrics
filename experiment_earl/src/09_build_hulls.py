#!/usr/bin/env python3
"""Per user: raw sessions -> chunks shifted to (0, 0) -> convex hull -> concave hull of every chunk point."""

import argparse
import json
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from shapely import MultiPoint, concave_hull

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")


def user_chunks(config: dict, user: str) -> tuple[list[np.ndarray], list[str]]:
    """Every chunk as its (x, y) path shifted so it starts at (0, 0), from the user's first
    `sessions_per_user` sessions (same pool order as the notebook), and the sessions used."""
    sessions = cfg_mod.session_pool(config, user, config["seed"])[: config["sessions_per_user"]]
    paths = []
    for folder, name in sessions:
        chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / folder / user / name), config)
        paths += [chunk[:, :2] - chunk[0, :2] for chunk, _ in chunks]
    return paths, [f"{folder}/{name}" for folder, name in sessions]


def coordinates(geometry) -> list[list[float]]:
    return [list(p) for p in geometry.exterior.coords] if geometry.geom_type == "Polygon" else []


def draw(ax, user: str, paths: list[np.ndarray], highlight: list[int], convex, concave, small: bool = False) -> None:
    """All chunks as faint gray lines, the `highlight` chunks as bold coloured lines with a dot at their end."""
    ax.add_collection(LineCollection(paths, colors="0.55", linewidths=0.3, alpha=0.25, rasterized=True))
    colours = plt.get_cmap("tab20")
    for n, i in enumerate(highlight):
        path, colour = paths[i], colours(n % 20)
        ax.plot(path[:, 0], path[:, 1], color=colour, linewidth=0.9 if small else 1.6, zorder=3)
        ax.plot(*path[-1], "o", color=colour, markersize=2 if small else 4, zorder=4)
    if convex.geom_type == "Polygon":
        ax.plot(*convex.exterior.xy, color="tab:gray", linestyle="--", linewidth=1,
                label=f"convex {convex.area / 1e6:.2f}M px²")
    if concave.geom_type == "Polygon":
        ax.fill(*concave.exterior.xy, color="tab:orange", alpha=0.25)
        ax.plot(*concave.exterior.xy, color="tab:orange", linewidth=1, label=f"concave {concave.area / 1e6:.2f}M px²")
    ax.plot(0, 0, "kx")
    ax.set_aspect("equal")
    ax.invert_yaxis()  # screen y grows downward
    ax.set_title(user, fontsize=9 if small else 11)
    ax.legend(fontsize=6 if small else 8, loc="upper right")
    if small:
        ax.tick_params(labelsize=6)
    else:
        ax.set_xlabel("Δx from chunk start (px)")
        ax.set_ylabel("Δy from chunk start (px)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    parser.add_argument("--highlight", type=int, default=30, help="random chunks per user drawn in colour (0 = none)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    print(cfg_mod.describe_data(config))
    if config["sessions_per_user"] > cfg_mod.max_sessions(config):
        raise SystemExit(f"sessions_per_user = {config['sessions_per_user']} but some user has only "
                         f"{cfg_mod.max_sessions(config)} sessions; lower it in config.yaml")
    users = [u for u in cfg_mod.list_users(config) if not args.user or u in args.user]
    out, figures = run / "hulls", run / "figures" / "hulls"
    out.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)

    built, rows = {}, []
    for user in users:
        paths, sessions = user_chunks(config, user)
        n_chunks = len(paths)
        points = np.vstack(paths) if paths else np.empty((0, 2))
        unique = np.unique(points, axis=0)  # the hulls only depend on distinct points
        highlight = random.Random(f"{config['seed']}-{user}-highlight").sample(range(n_chunks), min(args.highlight, n_chunks))
        cloud = MultiPoint(unique)
        convex, concave = cloud.convex_hull, concave_hull(cloud, ratio=config["concave_ratio"])
        built[user] = (paths, highlight, convex, concave)
        rows.append({"user": user, "sessions": len(sessions), "chunks": n_chunks, "points": len(points),
                     "unique_points": len(unique), "convex_area": round(convex.area),
                     "concave_area": round(concave.area),
                     "concave_share_of_convex": round(concave.area / convex.area, 3) if convex.area else None})
        (out / f"{user}.json").write_text(json.dumps({
            **rows[-1], "session_list": sessions, "concave_ratio": config["concave_ratio"],
            "convex_hull": coordinates(convex), "concave_hull": coordinates(concave),
        }, indent=2) + "\n")

        fig, ax = plt.subplots(figsize=(7, 7))
        draw(ax, user, paths, highlight, convex, concave)
        ax.set_title(f"{user}: {n_chunks:,} chunks from {len(sessions)} sessions, {len(highlight)} highlighted")
        fig.tight_layout()
        fig.savefig(figures / f"{user}.png", dpi=120)
        plt.close(fig)
        print(f"{user}: {len(sessions)} sessions, {n_chunks:,} chunks, {len(points):,} points | "
              f"convex {convex.area / 1e6:.2f}M px², concave {concave.area / 1e6:.2f}M px²", flush=True)

    summary = pd.DataFrame(rows)
    summary.to_csv(out / "summary.csv", index=False)

    cols = 5
    rows_n = -(-len(built) // cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(cols * 3.6, rows_n * 3.6), squeeze=False)
    for ax, (user, (paths, highlight, convex, concave)) in zip(axes.ravel(), built.items()):
        draw(ax, user, paths, highlight, convex, concave, small=True)
    for ax in axes.ravel()[len(built):]:
        ax.axis("off")
    fig.suptitle(f"Chunks (gray, {args.highlight} per user in colour), convex (dashed) and concave (orange) hulls, {config['sessions_per_user']} sessions per user, "
                 f"concave_ratio {config['concave_ratio']}")
    fig.tight_layout()
    fig.savefig(figures / "all_users.png", dpi=120)
    plt.close(fig)
    print(f"Output: {out}, {figures}")


if __name__ == "__main__":
    main()
