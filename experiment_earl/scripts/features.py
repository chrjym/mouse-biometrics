"""Shape and timing features of the raw mouse path inside each 1-second chunk.

A chunk keeps Earl's end points (the first event at or after t and at or after
t + 1) and adds every event between them, so it describes how the cursor got
from (0, 0) to the end point, not only where it ended up.
"""

from pathlib import Path

import numpy as np

from chunking import load_session, second_boundaries

FEATURES = [
    "dx",                 # net horizontal displacement (px), Earl's chunk end point
    "dy",                 # net vertical displacement (px), screen y grows downward
    "path_length",        # total distance travelled along the path (px)
    "straightness",       # net displacement / path length: 1 = straight line, ~0 = loop or zig-zag
    "mean_speed",         # mean speed between consecutive events (px/s)
    "max_speed",          # fastest step (px/s)
    "curvature",          # total turning / path length (rad/px): how bendy the path is
    "total_turning",      # sum of absolute turning angles between steps (rad)
    "direction_changes",  # turns sharper than `turn_degrees`
    "pauses",             # stretches longer than `pause_ms` without movement (the hand stopped)
]


def resample(x: np.ndarray, y: np.ndarray, t: np.ndarray, step_s: float) -> tuple[np.ndarray, ...]:
    """Positions every `step_s` seconds, holding the last logged position (Balabit only
    logs while the mouse moves, so interpolating would invent motion during pauses).
    The first and last events are kept so dx and dy are unchanged."""
    t = np.maximum.accumulate(t)  # one Balabit session has a client timestamp that steps back
    grid = np.append(np.arange(t[0], t[-1], step_s), t[-1])
    index = np.searchsorted(t, grid, side="right") - 1
    index[0] = 0
    return x[index], y[index], grid


def count_pauses(step: np.ndarray, dt: np.ndarray, pause_s: float) -> int:
    """Stretches longer than `pause_s` without movement: the time from one moving
    step (or the chunk start) to the next one, plus the still tail of the chunk."""
    elapsed = np.cumsum(dt)
    moved_at = elapsed[step > 0]
    if not len(moved_at):
        return int(elapsed[-1] > pause_s) if len(elapsed) else 0
    gaps = np.diff(moved_at, prepend=0.0)
    return int(np.sum(gaps > pause_s) + (elapsed[-1] - moved_at[-1] > pause_s))


def path_features(x: np.ndarray, y: np.ndarray, t: np.ndarray, pause_s: float, turn_rad: float) -> dict:
    """Features of one path given its x, y and timestamps (seconds)."""
    step_x, step_y, dt = np.diff(x), np.diff(y), np.diff(t)
    step = np.hypot(step_x, step_y)
    path_length = step.sum()
    net = np.hypot(x[-1] - x[0], y[-1] - y[0])

    timed = dt > 0  # client timestamps tie occasionally; skip those steps for speed
    speed = step[timed] / dt[timed]

    moving = step > 0
    heading = np.arctan2(step_y[moving], step_x[moving])
    turn = np.abs(np.angle(np.exp(1j * np.diff(heading))))  # wrapped to [0, pi]

    return {
        "dx": x[-1] - x[0],
        "dy": y[-1] - y[0],
        "path_length": path_length,
        "straightness": net / path_length if path_length else 0.0,
        "mean_speed": speed.mean() if len(speed) else 0.0,
        "max_speed": speed.max() if len(speed) else 0.0,
        "curvature": turn.sum() / path_length if path_length else 0.0,
        "total_turning": turn.sum(),
        "direction_changes": int(np.sum(turn > turn_rad)),
        "pauses": count_pauses(step, dt, pause_s),
    }


def session_features(
    session_path: Path,
    interval: float = 1.0,
    pause_ms: float = 200,
    turn_degrees: float = 45,
    resample_ms: float = 0,
) -> np.ndarray:
    """One row of FEATURES per chunk in which the cursor moved (path length > 0), in time order.
    `resample_ms` > 0 puts every path on the same time grid before measuring it."""
    record, client, xs, ys = load_session(session_path)
    if len(record) < 2:
        return np.empty((0, len(FEATURES)))
    _, index = second_boundaries(record, interval)
    rows = []
    for start, end in zip(index[:-1], index[1:]):
        if end == start:
            continue
        x, y, t = xs[start : end + 1], ys[start : end + 1], client[start : end + 1]
        if resample_ms > 0:
            x, y, t = resample(x, y, t, resample_ms / 1000)
        features = path_features(x, y, t, pause_ms / 1000, np.radians(turn_degrees))
        if features["path_length"] > 0:
            rows.append([features[name] for name in FEATURES])
    return np.array(rows, dtype=float).reshape(-1, len(FEATURES))
