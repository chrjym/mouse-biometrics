#!/usr/bin/env python3
"""Automate first-movement capture for SapiMouse sessions."""

import argparse
from pathlib import Path

from capture_first_movement import capture_directory

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data/sapimouse")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/sapimouse_first_movements")
    parser.add_argument("--pattern", default="*.csv")
    parser.add_argument("--min-step-px", type=float, default=3.0)
    parser.add_argument("--sustain-points", type=int, default=3)
    parser.add_argument("--idle-ms", type=float, default=100.0)
    parser.add_argument("--max-duration-ms", type=float, default=1000.0)
    args = parser.parse_args()

    summary, summary_path = capture_directory(
        args.input_dir,
        args.output_dir,
        args.pattern,
        "milliseconds",
        {
            "min_step_px": args.min_step_px,
            "sustain_points": args.sustain_points,
            "idle_ms": args.idle_ms,
            "max_duration_ms": args.max_duration_ms,
        },
    )
    print(f"SapiMouse sessions processed: {summary['processed']}")
    print(f"SapiMouse sessions failed: {summary['failed']}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
