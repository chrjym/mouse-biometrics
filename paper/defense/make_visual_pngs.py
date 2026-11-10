#!/usr/bin/env python3
"""Process overview and two-experiments visuals as transparent PNGs (no slide title, logo or background)."""
import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from matplotlib.patches import FancyArrow  # noqa: E402
from make_matching_png import GREEN, arrow, plt, rbox, t  # noqa: E402  (also registers the Carlito font)
from make_experiments_slide import EXPERIMENTS, ROWS  # noqa: E402
from make_process_overview import STEPS  # noqa: E402


def canvas(w: float, h: float):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-0.02, w - 0.02)
    ax.set_ylim(h, 0)
    ax.axis("off")
    return fig, ax


def process_overview(out: Path, dpi: int) -> None:
    width, gap, height, head = 1.98, 0.35, 3.7, 1.0
    fig, ax = canvas(5 * width + 4 * gap + 0.04, height + 0.06)
    for i, (title, lines) in enumerate(STEPS):
        x = i * (width + gap)
        rbox(ax, x, 0.03, width, height)
        rbox(ax, x, 0.03, width, head, fill=GREEN, edge=None)
        t(ax, x + width / 2, 0.03 + head / 2, f"{i + 1}\n" + "\n".join(textwrap.wrap(title, 20)), 13, True, "white")
        y = 0.03 + head + 0.18
        for line in lines:
            wrapped = textwrap.wrap("• " + line, 25)
            t(ax, x + 0.1, y, "\n".join(wrapped), 11, ha="left", va="top")
            y += 0.19 * len(wrapped) + 0.11
        if i < len(STEPS) - 1:
            arrow(ax, x + width + 0.04, 0.03 + height / 2, gap - 0.08)
    fig.savefig(out, dpi=dpi, transparent=True)
    plt.close(fig)


def two_experiments(out: Path, dpi: int) -> None:
    w, gap, h, head = 5.0, 1.25, 3.75, 0.85
    fig, ax = canvas(2 * w + gap + 0.04, h + 0.95)
    top = 0.03
    for i, (name, goal, values) in enumerate(EXPERIMENTS):
        x = i * (w + gap)
        rbox(ax, x, top, w, h)
        rbox(ax, x, top, w, head, fill=GREEN, edge=None)
        t(ax, x + w / 2, top + 0.27, name, 13, True, "white")
        t(ax, x + w / 2, top + 0.57, goal, 18, True, "white")
        row_h = (h - head - 0.15) / len(ROWS)
        for j, (key, value) in enumerate(zip(ROWS, values)):
            y = top + head + 0.1 + j * row_h
            if j:
                ax.plot([x + 0.12, x + w - 0.12], [y - 0.03, y - 0.03], color=GREEN, lw=0.75)
            t(ax, x + 0.15, y + row_h / 2 - 0.03, key, 12, True, GREEN, ha="left")
            t(ax, x + 1.75, y + row_h / 2 - 0.03, "\n".join(textwrap.wrap(value, 36)), 13, ha="left")
    ax_x = w + 0.12
    ax.add_patch(FancyArrow(ax_x, top + h / 2, gap - 0.24, 0, width=0.3, head_width=0.6, head_length=0.3,
                            length_includes_head=True, fc=GREEN, ec="none"))
    t(ax, ax_x + (gap - 0.24) / 2, top + h / 2 - 0.55, "best\nsensitivity", 11, True, GREEN)
    t(ax, 0.0, top + h + 0.3, "Graphs: each setting's counts are added to the ones before it (running total). "
                              "Confusion matrix of each experiment = total at its last setting.", 12, ha="left")
    t(ax, 0.0, top + h + 0.6, "Output → best sensitivity and number of sessions, used to build each user's profile.",
      12, True, GREEN, ha="left")
    fig.savefig(out, dpi=dpi, transparent=True)
    plt.close(fig)


def main() -> None:
    here = Path(__file__).resolve().parent / "figures"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()
    process_overview(here / "process_overview_diagram.png", args.dpi)
    two_experiments(here / "two_experiments_diagram.png", args.dpi)
    print(f"2 transparent PNGs at {args.dpi} dpi -> {here}")


if __name__ == "__main__":
    main()
