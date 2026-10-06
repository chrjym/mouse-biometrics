"""Split a Balabit session into 1-second chunks whose start point is moved to (0, 0).

Same logic as temp/position_by_time.py + temp/build_chunks.py: the position at
second t is the first event whose record timestamp is >= t, and chunk t goes from
the position at t (shifted to the origin) to the position at t + 1.
"""

import csv
from pathlib import Path

import numpy as np

# Balabit logs x = y = 65535 for a few events; they are logging glitches, not positions.
INVALID_COORDINATE = 65535

VECTOR_COLUMNS = ["target_time", "timestamp", "x", "y", "vector_x", "vector_y", "vector_magnitude"]
CHUNK_COLUMNS = [
    "chunk_index",
    "t",
    "t_plus_1",
    "t_x_abs",
    "t_y_abs",
    "t_plus_1_x_abs",
    "t_plus_1_y_abs",
    "t_x_rel",
    "t_y_rel",
    "t_plus_1_x_rel",
    "t_plus_1_y_rel",
    "is_burn_in",
]


def load_session(session_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return record timestamps (seconds), x and y of every valid event, in file order."""
    timestamps, xs, ys = [], [], []
    with session_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            x, y = float(row["x"]), float(row["y"])
            if x >= INVALID_COORDINATE or y >= INVALID_COORDINATE:
                continue
            timestamps.append(float(row["record timestamp"]))
            xs.append(x)
            ys.append(y)
    return np.array(timestamps), np.array(xs), np.array(ys)


def build_vectors(session_path: Path, interval: float = 1.0) -> list[dict]:
    """Sample the first event at or after every `interval` seconds (the vectors.csv rows).

    Record timestamps never decrease within a file, so a binary search in file
    order picks the first matching row, even among the many tied timestamps.
    """
    timestamps, xs, ys = load_session(session_path)
    if len(timestamps) < 2:
        return []
    targets = np.arange(timestamps[0], timestamps[-1] + 1e-9, interval)
    index = np.searchsorted(timestamps, targets, side="left")
    x, y = xs[index], ys[index]
    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    columns = zip(targets, timestamps[index], x, y, dx, dy, np.hypot(dx, dy))
    return [dict(zip(VECTOR_COLUMNS, map(float, values))) for values in columns]


def mark_burn_in(moving: list[bool], idle_seconds: int) -> list[bool]:
    """Flag the first moving chunk of the session and the first one after
    `idle_seconds` or more idle chunks (idea #1, recorded but not used yet)."""
    flags = []
    idle_run = idle_seconds  # the session start counts as coming out of idle
    for is_moving in moving:
        flags.append(is_moving and idle_run >= idle_seconds)
        idle_run = 0 if is_moving else idle_run + 1
    return flags


def build_chunks(vectors: list[dict], idle_seconds: int = 5) -> list[dict]:
    """One chunk per consecutive (t, t + 1) pair, with t moved to (0, 0)."""
    chunks = []
    for i in range(len(vectors) - 1):
        start, end = vectors[i], vectors[i + 1]
        chunks.append(
            {
                "chunk_index": i,
                "t": start["target_time"],
                "t_plus_1": end["target_time"],
                "t_x_abs": start["x"],
                "t_y_abs": start["y"],
                "t_plus_1_x_abs": end["x"],
                "t_plus_1_y_abs": end["y"],
                "t_x_rel": 0.0,
                "t_y_rel": 0.0,
                "t_plus_1_x_rel": end["x"] - start["x"],
                "t_plus_1_y_rel": end["y"] - start["y"],
            }
        )
    moving = [c["t_plus_1_x_rel"] != 0 or c["t_plus_1_y_rel"] != 0 for c in chunks]
    for chunk, flag in zip(chunks, mark_burn_in(moving, idle_seconds)):
        chunk["is_burn_in"] = flag
    return chunks


def write_csv(rows: list[dict], columns: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
