#!/usr/bin/env python3
"""Build each Balabit user's profile: 3 random sessions -> 1-second chunks -> convex hull -> concave hull."""

import argparse
import json
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely import concave_hull
from shapely.geometry import MultiPoint

from chunking import CHUNK_COLUMNS, VECTOR_COLUMNS, build_chunks, build_vectors, write_csv

ROOT = Path(__file__).resolve().parents[1]


def hull_coordinates(geometry) -> list[list[float]]:
    return [list(point) for point in geometry.exterior.coords] if geometry.geom_type == "Polygon" else []


def plot_profile(user_id: str, points: list[tuple[float, float]], convex, concave, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(*zip(*points), s=3, alpha=0.3, color="tab:blue", label=f"chunk end points ({len(points):,})")
    if convex.geom_type == "Polygon":
        ax.plot(*convex.exterior.xy, color="tab:gray", linestyle="--", label=f"convex hull ({convex.area:,.0f} px²)")
    if concave.geom_type == "Polygon":
        ax.fill(*concave.exterior.xy, color="tab:orange", alpha=0.25)
        ax.plot(*concave.exterior.xy, color="tab:orange", label=f"concave hull ({concave.area:,.0f} px²)")
    ax.scatter([0], [0], color="black", marker="x", label="start (0, 0)")
    ax.set_title(f"{user_id}: 1-second chunks of 3 sessions")
    ax.set_xlabel("Δx (px)")
    ax.set_ylabel("Δy (px)")
    ax.set_aspect("equal")
    ax.invert_yaxis()  # screen y grows downward
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def build_profile(user_dir: Path, output_dir: Path, args: argparse.Namespace) -> dict:
    sessions = sorted(path for path in user_dir.iterdir() if path.is_file())
    selected = random.Random(f"{args.seed}-{user_dir.name}").sample(sessions, args.sessions)
    user_output = output_dir / user_dir.name

    points = []
    chunk_count = burn_in_count = 0
    for session_path in selected:
        vectors = build_vectors(session_path, args.interval)
        chunks = build_chunks(vectors, args.idle_seconds)
        write_csv(vectors, VECTOR_COLUMNS, user_output / session_path.name / "vectors.csv")
        write_csv(chunks, CHUNK_COLUMNS, user_output / session_path.name / "chunks.csv")
        chunk_count += len(chunks)
        burn_in_count += sum(chunk["is_burn_in"] for chunk in chunks)
        points += [(chunk["t_plus_1_x_rel"], chunk["t_plus_1_y_rel"]) for chunk in chunks]

    cloud = MultiPoint(points)
    convex = cloud.convex_hull
    concave = concave_hull(cloud, ratio=args.concave_ratio)
    plot_profile(user_dir.name, points, convex, concave, user_output / "profile.png")

    profile = {
        "user_id": user_dir.name,
        "sessions": [path.name for path in selected],
        "settings": {
            "sessions": args.sessions,
            "seed": args.seed,
            "interval_s": args.interval,
            "idle_seconds": args.idle_seconds,
            "concave_ratio": args.concave_ratio,
        },
        "chunk_count": chunk_count,
        "idle_chunk_count": sum(point == (0.0, 0.0) for point in points),
        "burn_in_count": burn_in_count,
        "convex_hull": {"area": convex.area, "coordinates": hull_coordinates(convex)},
        "concave_hull": {"area": concave.area, "coordinates": hull_coordinates(concave)},
    }
    with (user_output / "profile.json").open("w") as handle:
        json.dump(profile, handle, indent=2)
        handle.write("\n")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "datasets/balabit/training_files")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    parser.add_argument("--sessions", type=int, default=3, help="random sessions per user")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--interval", type=float, default=1.0, help="chunk length in seconds")
    parser.add_argument("--idle-seconds", type=int, default=5, help="idle gap before a burn-in chunk")
    parser.add_argument("--concave-ratio", type=float, default=0.1, help="0 = tightest, 1 = convex hull")
    args = parser.parse_args()

    user_dirs = sorted(path for path in args.input_dir.iterdir() if path.is_dir())
    if args.user:
        user_dirs = [path for path in user_dirs if path.name in set(args.user)]

    summary = []
    for user_dir in user_dirs:
        profile = build_profile(user_dir, args.output_dir, args)
        summary.append({key: profile[key] for key in ("user_id", "sessions", "chunk_count", "burn_in_count")})
        summary[-1]["convex_area"] = profile["convex_hull"]["area"]
        summary[-1]["concave_area"] = profile["concave_hull"]["area"]
        print(
            f"{profile['user_id']}: {profile['chunk_count']:,} chunks "
            f"({profile['idle_chunk_count']:,} idle, {profile['burn_in_count']:,} burn-in), "
            f"convex {profile['convex_hull']['area'] / 1e6:.2f}M px², "
            f"concave {profile['concave_hull']['area'] / 1e6:.2f}M px²"
        )

    summary_path = args.output_dir / "summary.json"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w") as handle:
        json.dump({"profiles": summary}, handle, indent=2)
        handle.write("\n")
    print(f"Profiles built: {len(summary)}")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
