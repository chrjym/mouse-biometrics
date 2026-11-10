#!/usr/bin/env python3
"""DTW matching diagram (stroke -> library -> smallest distance -> sensitivity; session 20% rule) as a transparent PNG."""
import argparse
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import FancyArrow, FancyBboxPatch, Polygon  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_matching_slide import SESSIONS, strokes  # noqa: E402

GREEN, LIGHT, DARK, GREY, RED, BLUE = "#0C4B05", "#EEF5EC", "#1F1F1F", "#A6A6A6", "#B01E1E", "#1F5FBF"
W, H = 10.25, 3.9   # inches
for f in Path("/usr/share/fonts/truetype/crosextra").glob("Carlito-*.ttf"):  # Calibri-compatible, as on the slides
    font_manager.fontManager.addfont(str(f))
plt.rcParams["font.family"] = ["Carlito", "DejaVu Sans"]


def rbox(ax, x, y, w, h, fill=LIGHT, edge=GREEN, r=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fill,
                                ec=edge if edge else "none", lw=1.5))


def arrow(ax, x, y, w=0.3):
    ax.add_patch(FancyArrow(x, y, w, 0, width=0.16, head_width=0.34, head_length=0.14, length_includes_head=True,
                            fc=GREEN, ec="none"))


def stroke(ax, xy, cx, cy, size, color, lw):
    xy = xy - (xy.min(0) + xy.max(0)) / 2
    span = max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1])) or 1
    p = xy / span * size + [cx, cy]
    ax.plot(p[:, 0], p[:, 1], color=color, lw=lw, solid_capstyle="round")
    ax.plot(*p[0], "o", color=DARK, ms=4)


def t(ax, x, y, s, size=11, bold=False, color=DARK, ha="center", va="center"):
    ax.text(x, y, s, fontsize=size, fontweight="bold" if bold else "normal", color=color, ha=ha, va=va)


def stroke_row(ax, tested, library, drag):
    top, h = 0.05, 1.85
    mid = top + h / 2
    rbox(ax, 0.0, top, 1.6, h)
    t(ax, 0.8, top + 0.25, "Tested stroke", 14, True, GREEN)
    stroke(ax, tested, 0.8, top + 1.05, 0.95, BLUE, 2.5)
    arrow(ax, 1.65, mid)
    lx, lw = 2.0, 3.9
    rbox(ax, lx, top, lw, h)
    t(ax, lx + lw / 2, top + 0.25, "Library strokes (same type)", 14, True, GREEN)
    for i, s in enumerate(library):
        cx = lx + 0.38 + i * 0.6
        stroke(ax, s, cx, top + 0.95, 0.42, GREEN, 1.75)
        t(ax, cx, top + 1.52, f"d{chr(0x2081 + i)}", 13, True)
    stroke(ax, drag, lx + lw - 0.36, top + 0.95, 0.36, GREY, 1.25)
    ax.plot([lx + lw - 0.58, lx + lw - 0.14], [top + 0.73, top + 1.17], color=RED, lw=1.5)
    t(ax, lx + lw - 0.36, top + 1.52, "drag", 11)
    arrow(ax, lx + lw + 0.05, mid)
    sx = lx + lw + 0.4
    rbox(ax, sx, top, 1.7, h)
    t(ax, sx + 0.85, top + 0.25, "Smallest d", 14, True, GREEN)
    t(ax, sx + 0.85, top + 0.95, "min(d₁ … dₙ)", 14, True)
    t(ax, sx + 0.85, top + 1.3, "÷ 64 points", 13)
    arrow(ax, sx + 1.75, mid)
    dx = sx + 2.1
    ax.add_patch(Polygon([(dx, top + 0.62), (dx + 0.9, top), (dx + 1.8, top + 0.62), (dx + 0.9, top + 1.24)],
                         fc=GREEN, ec="none"))
    t(ax, dx + 0.9, top + 0.62, "d ≤\nsensitivity?", 12, True, "white")
    rbox(ax, dx, top + 1.33, 0.85, 0.52, fill=GREEN, edge=None, r=0.06)
    t(ax, dx + 0.425, top + 1.59, "Match", 13, True, "white")
    rbox(ax, dx + 0.95, top + 1.33, 0.85, 0.52, fill=GREY, edge=None, r=0.06)
    t(ax, dx + 1.375, top + 1.59, "No\nmatch", 12, True, "white")


SHORT = ["user29 (own)", "user16 (impostor)"]


def session_row(ax):
    top = 2.1
    t(ax, 0.0, top + 0.12, "Session: ≥ 20% of strokes match → accepted", 15, True, GREEN, ha="left")
    bx, bw, bh = 2.05, 5.95, 0.42
    for i, ((_, _, matched, total), who) in enumerate(zip(SESSIONS, SHORT)):
        y = top + 0.42 + i * 0.6
        t(ax, bx - 0.1, y + bh / 2, who, 13, True, ha="right")
        share = matched / total
        ok = share >= 0.2
        rbox(ax, bx, y, bw, bh, fill="#E6E6E6", edge=None, r=0.08)
        rbox(ax, bx, y, bw * share, bh, fill=GREEN if ok else RED, edge=None, r=0.08)
        t(ax, bx + bw - 0.12, y + bh / 2, f"{matched}/{total} = {share:.0%}", 13, True, ha="right")
        rbox(ax, bx + bw + 0.2, y, 1.5, bh, fill=GREEN if ok else RED, edge=None, r=0.08)
        t(ax, bx + bw + 0.95, y + bh / 2, "Accepted" if ok else "Rejected", 13, True, "white")
    x20 = bx + bw * 0.2
    ax.plot([x20, x20], [top + 0.34, top + 0.42 + 0.6 + bh + 0.06], color=DARK, lw=1.5, ls="--")
    t(ax, x20, top + 0.42 + 0.6 + bh + 0.2, "20%", 12, True)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", type=Path, required=True, help="experiment_earl/ folder with runs/a6e6f7/strokes")
    ap.add_argument("--out", type=Path, default=here / "figures/matching_dtw_diagram.png")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-0.02, W - 0.02)
    ax.set_ylim(H, 0)
    ax.axis("off")
    stroke_row(ax, *strokes(args.experiment))
    session_row(ax)
    fig.savefig(args.out, dpi=args.dpi, transparent=True)
    print(f"{W} x {H} in at {args.dpi} dpi, transparent -> {args.out}")


if __name__ == "__main__":
    main()
