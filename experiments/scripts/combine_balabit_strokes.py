#!/usr/bin/env python3
"""Flatten all Balabit trajectory strokes for selected users into Parquet."""

import argparse
import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_COLUMNS = [
    "user_id",
    "session_id",
    "stroke_id",
    "point_index",
    "x",
    "y",
    "timestamp_ms",
    "event_type",
    "button",
]


def flatten_user(input_dir: Path, user_id: str) -> list[dict]:
    rows = []
    user_dir = input_dir / user_id

    for session_path in sorted(user_dir.iterdir()):
        if not session_path.is_file():
            continue

        session_id = session_path.name
        stroke_id = 0
        point_index = 0
        in_stroke = False

        with session_path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            for event in reader:
                state = event["state"]
                if state in {"Pressed", "Released"}:
                    in_stroke = False
                    continue
                if state not in {"Move", "Drag"}:
                    continue

                if not in_stroke:
                    stroke_id += 1
                    point_index = 0
                    in_stroke = True

                rows.append(
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "stroke_id": stroke_id,
                        "point_index": point_index,
                        "x": float(event["x"]),
                        "y": float(event["y"]),
                        "timestamp_ms": float(event["client timestamp"]) * 1000,
                        "event_type": state,
                        "button": event["button"],
                    }
                )
                point_index += 1

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", required=True)
    parser.add_argument(
        "--input-dir", type=Path, default=ROOT / "data/balabit/training_files"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/balabit_user7_strokes.parquet"
    )
    args = parser.parse_args()

    rows = [row for user_id in args.user for row in flatten_user(args.input_dir, user_id)]
    frame = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    frame = frame.astype(
        {
            "user_id": "string",
            "session_id": "string",
            "stroke_id": "int64",
            "point_index": "int64",
            "x": "float64",
            "y": "float64",
            "timestamp_ms": "float64",
            "event_type": "string",
            "button": "string",
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(args.output, index=False)
    print(f"Wrote {len(frame):,} points across {frame.stroke_id.nunique():,} strokes")
    print(f"Users: {', '.join(args.user)}")
    print(f"Sessions: {frame.session_id.nunique():,}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()