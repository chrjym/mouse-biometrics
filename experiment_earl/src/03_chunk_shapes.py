#!/usr/bin/env python3
"""Split every session under temp/ into pause-based chunks and save them to shapes/ with a per-user library."""

import argparse
import json
from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

import numpy as np

cfg_mod = import_module("00_config")

MOVE, DRAG = 0, 1


def segment(df, config: dict) -> list[tuple[np.ndarray, int]]:
    """Raw chunks as ([x, y, t] array, kind). A new chunk starts after a pause or any click event."""
    click = df["state"].isin(["Pressed", "Released"]).to_numpy()
    clicks_before = np.cumsum(click)
    keep = ~click
    t = df["t"].to_numpy()[keep]
    if not len(t):
        return []
    xyt = np.column_stack([df["x"].to_numpy()[keep], df["y"].to_numpy()[keep], t])
    drag = (df["state"].to_numpy()[keep] == "Drag")
    clicked = np.diff(clicks_before[keep], prepend=clicks_before[keep][0]) > 0
    new_chunk = (np.diff(t, prepend=t[0]) > config["pause_gap_s"]) | clicked
    starts = np.flatnonzero(new_chunk)
    starts = np.concatenate([[0], starts[starts > 0], [len(t)]])
    chunks = []
    for lo, hi in zip(starts[:-1], starts[1:]):
        if hi - lo >= config["min_points"] and path_length(xyt[lo:hi]) >= config["min_length_px"]:
            chunks.append((xyt[lo:hi], DRAG if drag[lo:hi].mean() > 0.5 else MOVE))
    return chunks


def path_length(chunk: np.ndarray) -> float:
    return float(np.hypot(*np.diff(chunk[:, :2], axis=0).T).sum())


def normalize(chunk: np.ndarray, n: int) -> np.ndarray | None:
    """Start at the origin, bounding-box diagonal 1, n points evenly spaced by arc length."""
    xy = chunk[:, :2] - chunk[0, :2]
    diag = np.hypot(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]))
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    if diag == 0 or arc[-1] == 0:
        return None
    grid = np.linspace(0, arc[-1], n)
    return np.column_stack([np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])]) / diag


@dataclass
class Session:
    key: str                      # "<user>/<session>"
    n_chunks: int                 # every recorded chunk, including ones too flat to compare
    paths: dict[int, np.ndarray] = field(default_factory=dict)  # kind -> (m, n, 2) normalized chunks


def describe(key: str, chunks: list[tuple[np.ndarray, int]], config: dict) -> Session:
    session = Session(key, len(chunks))
    for kind in (MOVE, DRAG):
        paths = [normalize(c, config["resample_n"]) for c, k in chunks if k == kind]
        paths = [p for p in paths if p is not None]
        session.paths[kind] = np.array(paths).reshape(-1, config["resample_n"], 2)
    return session


def save_session(chunks: list[tuple[np.ndarray, int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = np.array([
        [kind, np.hypot(*np.diff(c[:, :2], axis=0).T).sum(), c[-1, 2] - c[0, 2]]
        for c, kind in chunks
    ]).reshape(-1, 3)  # kind, path length (px), duration (s)
    np.savez(path, meta=meta, **{f"chunk_{i}": c for i, (c, _) in enumerate(chunks)})


def load_chunks(path: Path) -> list[tuple[np.ndarray, int]]:
    data = np.load(path)
    return [(data[f"chunk_{i}"], int(kind)) for i, kind in enumerate(data["meta"][:, 0])]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = cfg_mod.load_config()
    root = cfg_mod.ROOT
    for label in ("legitimate", "impostor"):
        library = {}
        for user_dir in sorted((root / "temp" / label).iterdir()):
            counts, lengths = [], []
            for session_path in sorted(user_dir.iterdir()):
                chunks = segment(cfg_mod.load_session(session_path), config)
                save_session(chunks, root / "shapes" / label / user_dir.name / f"{session_path.name}.npz")
                counts.append(len(chunks))
                lengths += [len(c) for c, _ in chunks]
                if label == "legitimate":
                    for kind, paths in describe(session_path.name, chunks, config).paths.items():
                        library.setdefault(kind, []).append(paths)
            print(f"{label:10} {user_dir.name:7} {len(counts)} sessions, {sum(counts):,} chunks, "
                  f"{np.mean(lengths):.1f} points per chunk")
            if label == "legitimate":
                np.savez(root / "shapes" / label / user_dir.name / "library.npz",
                         **{("drag" if k else "move"): np.concatenate(v) for k, v in library.items()})
                library = {}
    print(f"Output: {root / 'shapes'}")


if __name__ == "__main__":
    main()
