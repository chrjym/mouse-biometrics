#!/usr/bin/env python3
"""Per user: raw sessions -> chunks shifted to (0, 0) -> chunk end points -> convex hull -> concave hull."""

import argparse
import json
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import MultiPoint, concave_hull

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")


def end_points(config: dict, user: str) -> tuple[np.ndarray, list[str]]:
    """One point per chunk: where it ends once its start is moved to (0, 0), i.e. its net movement (dx, dy).
    Uses the user's first `sessions_per_user` sessions (same pool order as the notebook)."""
    sessions = cfg_mod.session_pool(config, user, config["seed"])[: config["sessions_per_user"]]
    points = []
    for folder, name in sessions:
        chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / folder / user / name), config)
        points += [chunk[-1, :2] - chunk[0, :2] for chunk, _ in chunks]
    return np.array(points).reshape(-1, 2), [f"{folder}/{name}" for folder, name in sessions]


def coordinates(geometry) -> list[list[float]]:
    return [list(p) for p in geometry.exterior.coords] if geometry.geom_type == "Polygon" else []


def draw(ax, user: str, points: np.ndarray, convex, concave, small: bool = False) -> None:
    ax.scatter(points[:, 0], points[:, 1], s=1 if small else 3, alpha=0.3, color="tab:blue",
               label=f"chunk end points ({len(points):,})", rasterized=True)
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
    ax.legend(fontsize=6 if small else 8, loc="upper right", markerscale=4)
    if small:
        ax.tick_params(labelsize=6)
    else:
        ax.set_xlabel("dx: net horizontal movement of the chunk (px)")
        ax.set_ylabel("dy: net vertical movement of the chunk (px)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
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
        points, sessions = end_points(config, user)
        cloud = MultiPoint(np.unique(points, axis=0))
        convex, concave = cloud.convex_hull, concave_hull(cloud, ratio=config["concave_ratio"])
        built[user] = (points, convex, concave)
        distance = np.hypot(points[:, 0], points[:, 1])
        rows.append({
            "user": user, "sessions": len(sessions), "chunks": len(points),
            "zero_movement_chunks": int(np.sum(distance == 0)),
            "median_distance_px": round(float(np.median(distance)), 1) if len(points) else None,
            "convex_area": round(convex.area), "concave_area": round(concave.area),
            "concave_share_of_convex": round(concave.area / convex.area, 3) if convex.area else None,
        })
        (out / f"{user}.json").write_text(json.dumps({
            **rows[-1], "session_list": sessions, "concave_ratio": config["concave_ratio"],
            "convex_hull": coordinates(convex), "concave_hull": coordinates(concave),
        }, indent=2) + "\n")

        fig, ax = plt.subplots(figsize=(7, 7))
        draw(ax, user, points, convex, concave)
        ax.set_title(f"{user}: end points of {len(points):,} chunks from {len(sessions)} sessions")
        fig.tight_layout()
        fig.savefig(figures / f"{user}.png", dpi=120)
        plt.close(fig)
        print(f"{user}: {len(sessions)} sessions, {len(points):,} chunk end points | "
              f"convex {convex.area / 1e6:.2f}M px², concave {concave.area / 1e6:.2f}M px²", flush=True)

    pd.DataFrame(rows).to_csv(out / "summary.csv", index=False)

    cols = 5
    rows_n = -(-len(built) // cols)
    fig, axes = plt.subplots(rows_n, cols, figsize=(cols * 3.6, rows_n * 3.6), squeeze=False)
    for ax, (user, (points, convex, concave)) in zip(axes.ravel(), built.items()):
        draw(ax, user, points, convex, concave, small=True)
    for ax in axes.ravel()[len(built):]:
        ax.axis("off")
    fig.suptitle(f"Chunk end points (blue), convex (dashed) and concave (orange) hulls, "
                 f"{config['sessions_per_user']} sessions per user, concave_ratio {config['concave_ratio']}")
    fig.tight_layout()
    fig.savefig(figures / "all_users.png", dpi=120)
    plt.close(fig)
    print(f"Output: {out}, {figures}")


if __name__ == "__main__":
    main()
