#!/usr/bin/env python3
"""Build each Balabit user's initial profile from 1-second chunks of 3 random training sessions."""

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np
from shapely import concave_hull
from shapely.geometry import MultiPoint

from chunk_by_second import CHUNK_COLUMNS, chunk_session

ROOT = Path(__file__).resolve().parents[1]


def hull_coordinates(polygon) -> list[list[float]]:
    return [list(point) for point in polygon.exterior.coords] if polygon.geom_type == "Polygon" else []


def build_profile(
    user_dir: Path,
    output_dir: Path,
    sessions_per_user: int,
    seed: int,
    idle_seconds: int,
    concave_ratio: float,
    burn_in_only: bool,
) -> dict:
    sessions = sorted(path for path in user_dir.iterdir() if path.is_file())
    selected = random.Random(f"{seed}-{user_dir.name}").sample(sessions, sessions_per_user)

    user_output_dir = output_dir / user_dir.name
    user_output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = user_output_dir / "chunks.csv"
    rows = []
    with chunks_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["session_id", *CHUNK_COLUMNS])
        writer.writeheader()
        for session_path in selected:
            for chunk in chunk_session(session_path, idle_seconds):
                row = {"session_id": session_path.name, **chunk}
                writer.writerow(row)
                rows.append(row)

    key = "is_burn_in" if burn_in_only else "is_moving"
    endpoints = [(row["t_plus_1_x_rel"], row["t_plus_1_y_rel"]) for row in rows if row[key]]
    cloud = MultiPoint([(0.0, 0.0), *endpoints])
    convex = cloud.convex_hull
    concave = concave_hull(cloud, ratio=concave_ratio)

    profile = {
        "user_id": user_dir.name,
        "sessions": [path.name for path in selected],
        "settings": {
            "sessions_per_user": sessions_per_user,
            "seed": seed,
            "idle_seconds": idle_seconds,
            "concave_ratio": concave_ratio,
            "hull_points": "burn_in" if burn_in_only else "moving",
            "timestamp": "record timestamp",
            "interval_s": 1.0,
        },
        "chunk_count": len(rows),
        "moving_count": sum(row["is_moving"] for row in rows),
        "burn_in_count": sum(row["is_burn_in"] for row in rows),
        "hull_point_count": len(endpoints),
        "convex_hull": {"area": convex.area, "coordinates": hull_coordinates(convex)},
        "concave_hull": {"area": concave.area, "coordinates": hull_coordinates(concave)},
    }
    with (user_output_dir / "profile.json").open("w") as handle:
        json.dump(profile, handle, indent=2)
        handle.write("\n")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/balabit/training_files")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/balabit_initial_profiles")
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    parser.add_argument("--sessions-per-user", type=int, default=3)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--idle-seconds", type=int, default=5)
    parser.add_argument("--concave-ratio", type=float, default=0.1)
    parser.add_argument("--burn-in-only", action="store_true", help="build hulls from burn-in chunks only")
    args = parser.parse_args()

    user_dirs = sorted(path for path in args.input_dir.iterdir() if path.is_dir())
    if args.user:
        user_dirs = [path for path in user_dirs if path.name in set(args.user)]

    profiles = []
    for user_dir in user_dirs:
        profile = build_profile(
            user_dir,
            args.output_dir,
            args.sessions_per_user,
            args.seed,
            args.idle_seconds,
            args.concave_ratio,
            args.burn_in_only,
        )
        profiles.append(
            {
                "user_id": profile["user_id"],
                "sessions": profile["sessions"],
                "chunk_count": profile["chunk_count"],
                "moving_count": profile["moving_count"],
                "burn_in_count": profile["burn_in_count"],
                "convex_area": profile["convex_hull"]["area"],
                "concave_area": profile["concave_hull"]["area"],
            }
        )
        print(
            f"{profile['user_id']}: {profile['chunk_count']:,} chunks, {profile['moving_count']:,} moving, "
            f"{profile['burn_in_count']:,} burn-in, concave area {profile['concave_hull']['area'] / 1e6:.2f}M px²"
        )

    summary_path = args.output_dir / "summary.json"
    with summary_path.open("w") as handle:
        input_dir = args.input_dir.resolve()
        if input_dir.is_relative_to(ROOT.parent):
            input_dir = input_dir.relative_to(ROOT.parent)
        json.dump({"input_dir": str(input_dir), "profiles": profiles}, handle, indent=2)
        handle.write("\n")
    print(f"Profiles built: {len(profiles)}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
