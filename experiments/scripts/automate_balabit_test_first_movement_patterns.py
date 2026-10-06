#!/usr/bin/env python3
"""Create one first-movement pattern notebook per Balabit test user."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def notebook_for_user(user_id: str, capture_dir_name: str) -> dict:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {"id": f"{user_id}-intro", "language": "markdown"},
                "source": [
                    f"# Balabit test first-movement pattern: {user_id}\n",
                    "\n",
                    "This notebook reads the first movement from every test session for this user.\n",
                ],
            },
            {
                "cell_type": "code",
                "metadata": {"id": f"{user_id}-load", "language": "python"},
                "source": [
                    "from pathlib import Path\n",
                    "import json\n",
                    "\n",
                    "import matplotlib.pyplot as plt\n",
                    "import pandas as pd\n",
                    "\n",
                    f'USER_ID = "{user_id}"\n',
                    f'CAPTURE_DIR_NAME = "{capture_dir_name}"\n',
                    "PROJECT_ROOT = next(\n",
                    "    parent\n",
                    "    for parent in [Path.cwd(), *Path.cwd().parents]\n",
                    '    if (parent / "outputs").is_dir()\n',
                    ")\n",
                    "USER_DIR = PROJECT_ROOT / \"outputs\" / CAPTURE_DIR_NAME / USER_ID\n",
                    "\n",
                    "session_rows = []\n",
                    'for json_path in sorted(USER_DIR.glob("session_*.json")):\n',
                    "    with json_path.open() as handle:\n",
                    "        capture = json.load(handle)\n",
                    "    for point_index, point in enumerate(capture.get(\"points\", [])):\n",
                    "        session_rows.append({\n",
                    '            "session_id": json_path.stem,\n',
                    '            "point_index": point_index,\n',
                    '            "timestamp_ms": point["timestamp_ms"],\n',
                    '            "x": point["x"],\n',
                    '            "y": point["y"],\n',
                    '            "event_type": point["event_type"],\n',
                    '            "button": point["button"],\n',
                    "        })\n",
                    "\n",
                    "points = pd.DataFrame(session_rows)\n",
                    "if points.empty:\n",
                    '    raise ValueError(f"No first movements found for {USER_ID} in {USER_DIR}")\n',
                    "print(f\"User: {USER_ID}\")\n",
                    "print(f\"Sessions: {points['session_id'].nunique()}\")\n",
                    "print(f\"First-movement points: {len(points):,}\")\n",
                    "points\n",
                ],
            },
            {
                "cell_type": "code",
                "metadata": {"id": f"{user_id}-plot", "language": "python"},
                "source": [
                    "ordered_points = points.sort_values(\n",
                    '    "session_id",\n',
                    '    key=lambda values: values.str.replace("session_", "", regex=False).astype(int),\n',
                    ")\n",
                    "\n",
                    'x_values = ordered_points["x"].tolist()\n',
                    'y_values = ordered_points["y"].tolist()\n',
                    'session_labels = ordered_points["session_id"].str.replace("session_", "", regex=False).tolist()\n',
                    "\n",
                    "fig, ax = plt.subplots(figsize=(10, 7))\n",
                    "ax.plot(x_values, y_values, linewidth=1.8, color=\"tab:blue\", alpha=0.9, label=\"Session order\")\n",
                    "for x_value, y_value, session_label in zip(x_values, y_values, session_labels):\n",
                    "    ax.plot(x_value, y_value, marker=\"o\", linestyle=\"None\", markersize=7, label=f\"Session {session_label}\")\n",
                    "\n",
                    'ax.set_title(f"Test first-movement pattern in session order: {USER_ID}")\n',
                    'ax.set_xlabel("x position")\n',
                    'ax.set_ylabel("y position")\n',
                    "ax.invert_yaxis()\n",
                    "ax.grid(alpha=0.25)\n",
                    'ax.legend(title="Sessions", bbox_to_anchor=(1.02, 1), loc="upper left")\n',
                    "fig.tight_layout()\n",
                    "plt.show()\n",
                ],
            },
        ],
        "metadata": {"language": "python"},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "outputs/balabit_test_first_movements",
    )
    parser.add_argument(
        "--notebook-dir",
        type=Path,
        default=ROOT / "notebooks/balabit_test_first_movement_patterns",
    )
    parser.add_argument("--user", action="append")
    args = parser.parse_args()

    user_dirs = sorted(path for path in args.input_dir.iterdir() if path.is_dir())
    if args.user:
        requested_users = set(args.user)
        user_dirs = [path for path in user_dirs if path.name in requested_users]

    for user_dir in user_dirs:
        notebook_dir = args.notebook_dir / user_dir.name
        notebook_dir.mkdir(parents=True, exist_ok=True)
        notebook_path = notebook_dir / f"visualize_{user_dir.name}.ipynb"
        notebook = notebook_for_user(user_dir.name, args.input_dir.name)
        with notebook_path.open("w") as handle:
            json.dump(notebook, handle, indent=2)
            handle.write("\n")

    print(f"Pattern notebooks created: {len(user_dirs)}")
    print(f"Notebook directory: {args.notebook_dir}")


if __name__ == "__main__":
    main()
