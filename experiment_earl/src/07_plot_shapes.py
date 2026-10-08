#!/usr/bin/env python3
"""Draw every chunk saved by 03_chunk_shapes.py as a PNG under shapes/<class>/<user>/<session>/."""

import argparse
from importlib import import_module
from multiprocessing import Pool
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")

KIND_NAMES = {chunk_mod.MOVE: "move", chunk_mod.DRAG: "drag"}
KIND_COLORS = {chunk_mod.MOVE: "tab:blue", chunk_mod.DRAG: "tab:orange"}


def draw_chunk(ax, chunk: np.ndarray, kind: int, title: str | None = None) -> None:
    """Raw screen path: green dot = start, red dot = end, y grows downward as on screen."""
    ax.plot(chunk[:, 0], chunk[:, 1], color=KIND_COLORS[kind], linewidth=1.2)
    ax.plot(*chunk[0, :2], "o", color="tab:green", markersize=3)
    ax.plot(*chunk[-1, :2], "o", color="tab:red", markersize=3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.set_yticks([])
    if title:
        ax.set_title(title, fontsize=7)


def plot_session(args: tuple[Path, Path, int, bool]) -> tuple[str, int]:
    npz_path, out_dir, limit, overview = args
    chunks = chunk_mod.load_chunks(npz_path)[: limit or None]
    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(2, 2))
    for i, (chunk, kind) in enumerate(chunks):
        ax.clear()
        title = f"#{i} {KIND_NAMES[kind]} {chunk_mod.path_length(chunk):.0f}px {chunk[-1, 2] - chunk[0, 2]:.2f}s"
        draw_chunk(ax, chunk, kind, title)
        fig.savefig(out_dir / f"chunk_{i:04d}_{KIND_NAMES[kind]}.png", dpi=80)
    plt.close(fig)

    if overview and chunks:
        shown = chunks[:100]
        cols = 10
        rows = -(-len(shown) // cols)
        fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.2, rows * 1.2))
        for ax, (chunk, kind) in zip(np.ravel(axes), shown):
            draw_chunk(ax, chunk, kind)
        for ax in np.ravel(axes)[len(shown):]:
            ax.axis("off")
        fig.suptitle(f"{npz_path.parent.name}/{npz_path.stem}: first {len(shown)} of {len(chunks)} chunks "
                     "(blue = move, orange = drag)", fontsize=9)
        fig.tight_layout()
        fig.savefig(out_dir / "overview.png", dpi=90)
        plt.close(fig)
    return f"{npz_path.parent.name}/{npz_path.stem}", len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    parser.add_argument("--limit", type=int, default=0, help="max chunks per session (0 = all)")
    parser.add_argument("--no-overview", action="store_true", help="skip the per-session overview.png grid")
    parser.add_argument("--workers", type=int, default=4)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    _, run = cfg_mod.open_run(args.run)

    shapes = run / "shapes"
    saved = sorted(shapes.glob("*/*/session_*.npz"))
    if not saved:
        steps = "\n".join(f"  .venv/bin/python experiment_earl/src/{s}.py --run {run.name}"
                          for s in ("01_sample_users", "02_sample_sessions", "03_chunk_shapes"))
        raise SystemExit(f"Run {run.name} has no shapes yet (the notebook does not save them). Run steps 01-03 first:\n{steps}")
    jobs = [(npz, npz.with_suffix(""), args.limit, not args.no_overview)
            for npz in saved if not args.user or npz.parent.name in args.user]
    if not jobs:
        users = ", ".join(sorted({f"{npz.parent.name} ({npz.parent.parent.name})" for npz in saved}))
        raise SystemExit(f"No shapes for {', '.join(args.user)} in run {run.name}. Users with shapes: {users}")

    total = 0
    with Pool(args.workers) as pool:
        for name, count in pool.imap_unordered(plot_session, jobs):
            total += count
            print(f"{name}: {count:,} PNGs", flush=True)
    print(f"Sessions: {len(jobs)}  PNGs: {total:,}")
    print(f"Output: {shapes}/<class>/<user>/<session>/")


if __name__ == "__main__":
    main()
