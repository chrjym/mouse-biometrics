"""Split a Balabit session into 1-second chunks, each normalized to start at (0, 0).

Ported from experiments/initial_program (position_by_time.py + build_chunks.py):
the position at second t is the first event whose record timestamp is >= t, and
chunk t is the displacement from the position at t to the position at t + 1.
"""

import csv
from pathlib import Path

import numpy as np

# Balabit logs x = y = 65535 for a handful of events; they are not real positions.
INVALID_COORDINATE = 65535

CHUNK_COLUMNS = [
    "chunk_index",
    "t",
    "t_plus_1",
    "t_x_abs",
    "t_y_abs",
    "t_plus_1_x_abs",
    "t_plus_1_y_abs",
    "t_plus_1_x_rel",
    "t_plus_1_y_rel",
    "is_moving",
    "is_burn_in",
]


def load_session(session_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return record timestamps (seconds), x, and y for every valid event, in file order."""
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


def positions_by_second(
    timestamps: np.ndarray, xs: np.ndarray, ys: np.ndarray, interval: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """Sample the first event at or after each target time from the first to the last event.

    Record timestamps never decrease within a Balabit file, so a binary search in
    file order picks the same row as the original program, including among ties.
    """
    targets = np.arange(timestamps[0], timestamps[-1] + 1e-9, interval)
    index = np.searchsorted(timestamps, targets, side="left")
    return targets, np.column_stack([xs[index], ys[index]])


def mark_burn_in(vectors: np.ndarray, idle_seconds: int) -> tuple[np.ndarray, np.ndarray]:
    """Flag moving chunks, and burn-in chunks: the first movement of the session or
    the first movement after at least `idle_seconds` consecutive idle chunks."""
    is_moving = np.any(vectors != 0, axis=1)
    is_burn_in = np.zeros(len(vectors), dtype=bool)
    idle_run = idle_seconds  # the session start counts as coming out of idle
    for index, moving in enumerate(is_moving):
        if moving:
            is_burn_in[index] = idle_run >= idle_seconds
            idle_run = 0
        else:
            idle_run += 1
    return is_moving, is_burn_in


def chunk_session(session_path: Path, idle_seconds: int, interval: float = 1.0) -> list[dict]:
    """Build one row per (t, t + 1) chunk with absolute and origin-relative positions."""
    timestamps, xs, ys = load_session(session_path)
    if len(timestamps) < 2:
        return []
    targets, positions = positions_by_second(timestamps, xs, ys, interval)
    vectors = np.diff(positions, axis=0)
    is_moving, is_burn_in = mark_burn_in(vectors, idle_seconds)

    return [
        {
            "chunk_index": index,
            "t": targets[index],
            "t_plus_1": targets[index + 1],
            "t_x_abs": positions[index, 0],
            "t_y_abs": positions[index, 1],
            "t_plus_1_x_abs": positions[index + 1, 0],
            "t_plus_1_y_abs": positions[index + 1, 1],
            "t_plus_1_x_rel": vectors[index, 0],
            "t_plus_1_y_rel": vectors[index, 1],
            "is_moving": bool(is_moving[index]),
            "is_burn_in": bool(is_burn_in[index]),
        }
        for index in range(len(vectors))
    ]
