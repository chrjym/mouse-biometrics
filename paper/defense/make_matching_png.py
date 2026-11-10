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
W, H = 11.35, 4.75   # inches
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
    top, h = 0.08, 2.2
    mid = top + h / 2
    rbox(ax, 0.0, top, 1.9, h)
    t(ax, 0.95, top + 0.3, "1  One stroke of\nthe tested session", 12, True, GREEN)
    stroke(ax, tested, 0.95, top + 1.2, 1.0, BLUE, 2.5)
    t(ax, 0.95, top + h - 0.2, "move stroke", 10)
    arrow(ax, 1.96, mid)
    lx, lw = 2.33, 4.25
    rbox(ax, lx, top, lw, h)
    t(ax, lx + lw / 2, top + 0.24, "2  Compared with every same-type stroke", 12, True, GREEN)
    t(ax, lx + lw / 2, top + 0.5, "in the user's library (first k sessions)", 11)
    for i, s in enumerate(library):
        cx = lx + 0.45 + i * 0.66
        stroke(ax, s, cx, top + 1.17, 0.46, GREEN, 1.75)
        sub = chr(0x2081 + i)
        t(ax, cx, top + 1.68, f"d{sub}" + (" … dₙ" if i == len(library) - 1 else ""), 11, True)
    stroke(ax, drag, lx + lw - 0.4, top + 1.17, 0.38, GREY, 1.25)
    ax.plot([lx + lw - 0.65, lx + lw - 0.15], [top + 0.92, top + 1.42], color=RED, lw=1.5)
    t(ax, lx + lw - 0.4, top + 1.75, "drag\nskipped", 9)
    t(ax, lx + 0.1, top + h - 0.17, "d = DTW distance, warping band 10% of stroke length", 9, ha="left")
    arrow(ax, lx + lw + 0.06, mid)
    sx = lx + lw + 0.43
    rbox(ax, sx, top, 1.95, h)
    t(ax, sx + 0.975, top + 0.3, "3  Smallest distance", 12, True, GREEN)
    t(ax, sx + 0.975, top + 1.0, "d = min(d₁ … dₙ)", 13, True)
    t(ax, sx + 0.975, top + 1.32, "÷ 64 points", 12)
    t(ax, sx + 0.975, top + 1.6, "= distance per point", 10)
    arrow(ax, sx + 2.0, mid)
    dx = sx + 2.37
    ax.add_patch(Polygon([(dx, top + 0.82), (dx + 0.95, top + 0.1), (dx + 1.9, top + 0.82), (dx + 0.95, top + 1.54)],
                         fc=GREEN, ec="none"))
    t(ax, dx + 0.95, top + 0.82, "d ≤\nsensitivity?", 11, True, "white")
    rbox(ax, dx, top + 1.65, 0.88, 0.55, fill=GREEN, edge=None, r=0.06)
    t(ax, dx + 0.44, top + 1.925, "Yes\nmatch", 11, True, "white")
    rbox(ax, dx + 1.02, top + 1.65, 0.88, 0.55, fill=GREY, edge=None, r=0.06)
    t(ax, dx + 1.46, top + 1.925, "No\nno match", 11, True, "white")


def session_row(ax):
    top = 2.48
    t(ax, 0.0, top + 0.15,
      "Repeat for every stroke of the session → session accepted if matched strokes / all strokes ≥ 20%",
      13, True, GREEN, ha="left")
    bx, bw, bh = 3.0, 5.45, 0.42
    for i, (who, lib, matched, total) in enumerate(SESSIONS):
        y = top + 0.5 + i * 0.68
        t(ax, bx - 0.08, y + 0.13, who, 11, True, ha="right")
        t(ax, bx - 0.08, y + 0.33, f"vs {lib}", 9, ha="right")
        share = matched / total
        ok = share >= 0.2
        rbox(ax, bx, y, bw, bh, fill="#E6E6E6", edge=None, r=0.08)
        rbox(ax, bx, y, bw * share, bh, fill=GREEN if ok else RED, edge=None, r=0.08)
        t(ax, bx + bw - 0.12, y + bh / 2, f"{matched} of {total} strokes = {share:.0%}", 11, True, ha="right")
        rbox(ax, bx + bw + 0.2, y, 1.5, bh, fill=GREEN if ok else RED, edge=None, r=0.08)
        t(ax, bx + bw + 0.95, y + bh / 2, "Accepted" if ok else "Rejected", 12, True, "white")
    x20 = bx + bw * 0.2
    ax.plot([x20, x20], [top + 0.4, top + 0.5 + 0.68 + bh + 0.08], color=DARK, lw=1.5, ls="--")
    t(ax, x20, top + 0.5 + 0.68 + bh + 0.22, "20%", 11, True)
    t(ax, 0.0, H - 0.08, "Strokes drawn: real user29 strokes, normalized. Counts: run 19399f, split 1x5, "
                         "sensitivity 0.05, 1 session per user.", 9, ha="left", va="bottom")


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
