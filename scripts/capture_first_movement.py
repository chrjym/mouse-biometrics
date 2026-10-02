"""Capture the first Move or Drag point from every user session file."""

import csv
import json
from pathlib import Path


def _timestamp_ms(value: str, timestamp_unit: str) -> float:
    timestamp = float(value)
    if timestamp_unit == "seconds":
        return timestamp * 1000
    if timestamp_unit == "milliseconds":
        return timestamp
    raise ValueError(f"Unsupported timestamp unit: {timestamp_unit}")


def _capture_session(session_path: Path, timestamp_unit: str, settings: dict) -> dict:
    points = []
    with session_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("state") not in {"Move", "Drag"}:
                continue
            points.append(
                {
                    "timestamp_ms": _timestamp_ms(row["client timestamp"], timestamp_unit),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "event_type": row["state"],
                    "button": row["button"],
                }
            )
            break

    return {
        "source_file": str(session_path),
        "timestamp_unit": "milliseconds",
        "capture_phase": "first_point_only",
        "capture_rule": settings,
        "point_count": len(points),
        "start_timestamp_ms": points[0]["timestamp_ms"] if points else None,
        "end_timestamp_ms": points[-1]["timestamp_ms"] if points else None,
        "points": points,
    }


def capture_directory(
    input_dir: Path,
    output_dir: Path,
    pattern: str,
    timestamp_unit: str,
    settings: dict,
) -> tuple[dict, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    captures = []
    processed = 0
    failed = 0

    for user_dir in sorted(path for path in input_dir.iterdir() if path.is_dir()):
        user_output_dir = output_dir / user_dir.name
        user_output_dir.mkdir(parents=True, exist_ok=True)
        for session_path in sorted(user_dir.glob(pattern)):
            if not session_path.is_file():
                continue
            processed += 1
            output_path = user_output_dir / f"{session_path.name}.json"
            try:
                capture = _capture_session(session_path, timestamp_unit, settings)
                with output_path.open("w") as handle:
                    json.dump(capture, handle, indent=2)
                    handle.write("\n")
                captures.append(
                    {
                        "source_file": str(session_path),
                        "output_file": str(output_path),
                        "point_count": capture["point_count"],
                        "duration_ms": 0.0,
                    }
                )
            except (KeyError, OSError, ValueError):
                failed += 1

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "pattern": pattern,
        "processed": processed,
        "failed": failed,
        "captures": captures,
    }
    summary_path = output_dir / "summary.json"
    with summary_path.open("w") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    return summary, summary_path
