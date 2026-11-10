#!/usr/bin/env python3
"""One-slide deck: how a stroke and a session are matched with DTW, as editable shapes on the thesis deck layout."""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_process_overview import DARK, GREEN, LIGHT, WHITE, keep_only_new_slide, text  # noqa: E402

GREY = RGBColor(0xA6, 0xA6, 0xA6)
RED = RGBColor(0xB0, 0x1E, 0x1E)
TESTED = RGBColor(0x1F, 0x5F, 0xBF)

USER = "user29"
TESTED_STROKE = ("session_0136325499", 3)
LIBRARY_SESSION = "session_0270940804"
DRAG_SESSION = "session_0500745842"
# Real counts: runs/19399f/5_1_0.05_1/results/accuracy.csv (split 1x5, sensitivity 0.05, 1 session)
SESSIONS = [("user29, own session (legitimate)", "user29's library", 19, 66),
            ("user16 (impostor)", "user9's library, its best", 9, 65)]


def normalized(points: pd.DataFrame, stroke: int, n: int = 64) -> np.ndarray:
    """Same as the notebook's normalize: start at (0, 0), bounding-box diagonal 1, n points by arc length."""
    xy = points.loc[points.stroke == stroke, ["x", "y"]].to_numpy(float)
    xy -= xy[0]
    diag = np.hypot(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]))
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    grid = np.linspace(0, arc[-1], n)
    return np.c_[np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])] / diag


def strokes(root: Path) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    base = root / "runs/a6e6f7/strokes" / USER
    pts = lambda s: pd.read_csv(base / f"{s}_points.csv").dropna(subset=["stroke"])
    meta = lambda s: pd.read_csv(base / f"{s}.csv")
    tested = normalized(pts(TESTED_STROKE[0]), TESTED_STROKE[1])
    lib_meta, lib_pts = meta(LIBRARY_SESSION), pts(LIBRARY_SESSION)
    library = [normalized(lib_pts, s) for s in lib_meta.loc[lib_meta.kind == "move", "stroke"].head(5)]
    drag_meta = meta(DRAG_SESSION)
    drag = normalized(pts(DRAG_SESSION), int(drag_meta.loc[drag_meta.kind == "drag", "stroke"].iloc[0]))
    return tested, library, drag


def draw_stroke(slide, xy: np.ndarray, cx: float, cy: float, size: float, color: RGBColor, width: float = 2.0):
    """Polyline of a normalized stroke, centred in a size x size inch square at (cx, cy)."""
    xy = xy - (xy.min(0) + xy.max(0)) / 2
    span = max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1])) or 1
    pts = [(int(Inches(cx + x / span * size)), int(Inches(cy + y / span * size))) for x, y in xy]
    ff = slide.shapes.build_freeform(*pts[0], scale=1.0)
    ff.add_line_segments(pts[1:], close=False)
    shp = ff.convert_to_shape()
    shp.fill.background()
    shp.line.color.rgb, shp.line.width = color, Pt(width)
    shp.shadow.inherit = False
    start = slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(pts[0][0] - Inches(0.04)), Emu(pts[0][1] - Inches(0.04)),
                                   Inches(0.08), Inches(0.08))
    start.fill.solid(); start.fill.fore_color.rgb = DARK; start.line.fill.background(); start.shadow.inherit = False
    return shp


def box(slide, x, y, w, h, fill=LIGHT, line=GREEN, radius=0.08):
    b = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    b.adjustments[0] = radius
    b.fill.solid(); b.fill.fore_color.rgb = fill
    if line is None:
        b.line.fill.background()
    else:
        b.line.color.rgb, b.line.width = line, Pt(1.5)
    b.shadow.inherit = False
    return b


def label(slide, x, y, w, h, lines, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP):
    t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    t.text_frame.margin_left = t.text_frame.margin_right = Inches(0.04)
    text(t.text_frame, lines, align=align, anchor=anchor)
    for p in t.text_frame.paragraphs:
        p.space_after = Pt(2)
    return t


def arrow(slide, x, y, w=0.32):
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y - 0.17), Inches(w), Inches(0.34))
    a.fill.solid(); a.fill.fore_color.rgb = GREEN; a.line.fill.background(); a.shadow.inherit = False


def stroke_row(slide, tested, library, drag) -> None:
    top, h = 2.62, 2.2
    mid = top + h / 2
    # 1. tested stroke
    box(slide, 0.48, top, 1.9, h)
    label(slide, 0.5, top + 0.05, 1.86, 0.5, [("1  One stroke of", 12, True, GREEN), ("the tested session", 12, True, GREEN)])
    draw_stroke(slide, tested, 1.43, top + 1.3, 1.05, TESTED, 2.5)
    label(slide, 0.5, top + h - 0.36, 1.86, 0.3, [("move stroke", 10, False, DARK)])
    arrow(slide, 2.43, mid)
    # 2. library
    lx, lw = 2.8, 4.25
    box(slide, lx, top, lw, h)
    label(slide, lx + 0.02, top + 0.05, lw - 0.04, 0.5,
          [("2  Compared with every same-type stroke", 12, True, GREEN), ("in the user's library (first k sessions)", 11, False, DARK)])
    cell = 0.62
    for i, s in enumerate(library):
        cx = lx + 0.45 + i * (cell + 0.04)
        draw_stroke(slide, s, cx, top + 1.25, 0.48, GREEN, 1.75)
        last = " … dₙ" if i == len(library) - 1 else ""
        label(slide, cx - 0.3, top + 1.68, 0.6 + 0.3 * bool(last), 0.3, [(f"d{chr(0x2081 + i)}{last}", 11, True, DARK)],
              align=PP_ALIGN.LEFT if last else PP_ALIGN.CENTER)
    draw_stroke(slide, drag, lx + lw - 0.4, top + 1.25, 0.4, GREY, 1.25)
    x1 = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(lx + lw - 0.65), Inches(top + 1.0),
                                    Inches(lx + lw - 0.15), Inches(top + 1.5))
    x1.line.color.rgb, x1.line.width = RED, Pt(1.5)
    label(slide, lx + lw - 0.75, top + 1.62, 0.7, 0.45, [("drag", 9, False, DARK), ("skipped", 9, False, DARK)])
    label(slide, lx + 0.05, top + h - 0.33, lw - 0.85, 0.3,
          [("d = DTW distance, warping band 10% of stroke length", 9, False, DARK)])
    arrow(slide, lx + lw + 0.05, mid)
    # 3. smallest distance
    sx = lx + lw + 0.42
    b = box(slide, sx, top, 1.95, h)
    label(slide, sx + 0.02, top + 0.05, 1.91, 0.5, [("3  Smallest distance", 12, True, GREEN)])
    label(slide, sx + 0.02, top + 0.75, 1.91, 1.2,
          [("d = min(d₁ … dₙ)", 13, True, DARK), ("÷ 64 points", 12, False, DARK),
           ("= distance per point", 10, False, DARK)])
    arrow(slide, sx + 2.0, mid)
    # 4. decision
    dx = sx + 2.37
    d = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, Inches(dx - 0.1), Inches(top + 0.1), Inches(1.95), Inches(1.45))
    d.text_frame.margin_left = d.text_frame.margin_right = Inches(0)
    d.fill.solid(); d.fill.fore_color.rgb = GREEN; d.line.fill.background(); d.shadow.inherit = False
    text(d.text_frame, [("d ≤", 12, True, WHITE), ("sensitivity?", 11, True, WHITE)], align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    for p in d.text_frame.paragraphs:
        p.space_after = Pt(0)
    yes = box(slide, dx - 0.05, top + 1.62, 0.88, 0.55, fill=GREEN, line=None)
    text(yes.text_frame, [("Yes", 10, True, WHITE), ("match", 11, True, WHITE)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    no = box(slide, dx + 0.92, top + 1.62, 0.88, 0.55, fill=GREY, line=None)
    text(no.text_frame, [("No", 10, True, WHITE), ("no match", 11, True, WHITE)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    for s in (yes, no):
        for p in s.text_frame.paragraphs:
            p.space_after = Pt(0)


def session_row(slide) -> None:
    top = 5.0
    label(slide, 0.48, top, 11.3, 0.35,
          [("Repeat for every stroke of the session → session accepted if matched strokes / all strokes ≥ 20%",
            13, True, GREEN)], align=PP_ALIGN.LEFT)
    bx, bw, bh = 3.25, 5.6, 0.42
    for i, (who, lib, matched, total) in enumerate(SESSIONS):
        y = top + 0.5 + i * 0.68
        label(slide, 0.48, y - 0.04, 2.72, 0.5, [(who, 11, True, DARK), (f"vs {lib}", 9, False, DARK)], align=PP_ALIGN.RIGHT)
        bg = box(slide, bx, y, bw, bh, fill=RGBColor(0xE6, 0xE6, 0xE6), line=None, radius=0.2)
        share = matched / total
        ok = share >= 0.2
        fg = box(slide, bx, y, bw * share, bh, fill=GREEN if ok else RED, line=None, radius=0.2)
        label(slide, bx + bw - 2.6, y + 0.04, 2.5, 0.35,
              [(f"{matched} of {total} strokes = {share:.0%}", 11, True, DARK)], align=PP_ALIGN.RIGHT)
        verdict = box(slide, bx + bw + 0.2, y, 1.5, bh, fill=GREEN if ok else RED, line=None, radius=0.2)
        text(verdict.text_frame, [("Accepted" if ok else "Rejected", 12, True, WHITE)], align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        verdict.text_frame.paragraphs[0].space_after = Pt(0)
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(bx + bw * 0.2), Inches(top + 0.4),
                                      Inches(bx + bw * 0.2), Inches(top + 0.5 + 0.68 + bh + 0.08))
    line.line.color.rgb, line.line.width = DARK, Pt(1.5)
    line.line.dash_style = MSO_LINE_DASH_STYLE.DASH
    label(slide, bx + bw * 0.2 - 0.5, top + 0.5 + 0.68 + bh + 0.06, 1.0, 0.3, [("20%", 11, True, DARK)])
    label(slide, 0.48, 7.02, 11.3, 0.3,
          [("Strokes drawn: real user29 strokes, normalized. Counts: run 19399f, split 1x5, sensitivity 0.05, "
            "1 session per user.", 9, False, DARK)], align=PP_ALIGN.LEFT)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, required=True, help="the thesis deck .pptx (its layout is reused)")
    ap.add_argument("--experiment", type=Path, required=True, help="experiment_earl/ folder with runs/a6e6f7/strokes")
    ap.add_argument("--out", type=Path, default=here / "matching_dtw.pptx")
    args = ap.parse_args()
    prs = Presentation(args.template)
    slide = keep_only_new_slide(prs, "Chapter Intro")
    for ph in list(slide.placeholders):
        if ph.placeholder_format.type != 1:
            ph._element.getparent().remove(ph._element)
    title = slide.shapes.title
    title.left, title.top, title.width, title.height = Inches(0.48), Inches(1.44), Inches(8.89), Inches(0.88)
    title.text = "Matching Strokes with DTW"
    r = title.text_frame.paragraphs[0].runs[0]
    r.font.name, r.font.bold, r.font.size = "Garamond", True, Pt(40)
    stroke_row(slide, *strokes(args.experiment))
    session_row(slide)
    prs.save(args.out)
    print(f"1 slide, {len(SESSIONS)} session bars -> {args.out}")


if __name__ == "__main__":
    main()
