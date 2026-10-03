#!/usr/bin/env python3
"""Capture the first movement from every Balabit test session per user."""

import argparse
from pathlib import Path

from capture_first_movement import capture_directory


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "data/balabit/test_files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs/balabit_test_first_movements",
    )
    parser.add_argument("--pattern", default="*")
    parser.add_argument("--min-step-px", type=float, default=3.0)
    parser.add_argument("--sustain-points", type=int, default=3)
    parser.add_argument("--idle-ms", type=float, default=100.0)
    parser.add_argument("--max-duration-ms", type=float, default=1000.0)
    args = parser.parse_args()

    summary, summary_path = capture_directory(
        args.input_dir,
        args.output_dir,
        args.pattern,
        "seconds",
        {
            "min_step_px": args.min_step_px,
            "sustain_points": args.sustain_points,
            "idle_ms": args.idle_ms,
            "max_duration_ms": args.max_duration_ms,
        },
    )
    print(f"Balabit test sessions processed: {summary['processed']}")
    print(f"Balabit test sessions failed: {summary['failed']}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()