#!/usr/bin/env python3
"""One-slide deck: raw data -> confusion matrix flow as editable PowerPoint shapes, on the thesis deck's own layout."""
import argparse
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

GREEN = RGBColor(0x0C, 0x4B, 0x05)   # title green of the thesis deck
LIGHT = RGBColor(0xEE, 0xF5, 0xEC)
DARK = RGBColor(0x1F, 0x1F, 0x1F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

STEPS = [
    ("Balabit raw data", [
        "10 users, 1,676 sessions",
        "Record: timestamps, button, state, x, y",
        "405 illegal sessions removed",
        "1,271 sessions used"]),
    ("Clean & cut into strokes", [
        "Remove missing, scroll and invalid records",
        "New stroke after a pause > 0.5 s or a click",
        "Keep strokes with ≥ 10 points",
        "Label each stroke move or drag"]),
    ("Normalize strokes", [
        "Start point moved to (0,\u00a00)",
        "Scaled by bounding-box diagonal",
        "Resampled to 64 points"]),
    ("DTW matching (sensitivity, sessions)", [
        "Same-type strokes, 10% warping band",
        "Stroke matches: distance per point ≤ sensitivity",
        "Session accepted: ≥ 20% of strokes match",
        "Exp 1: sensitivity 0.01 to 1.00",
        "Exp 2: 5 to 40 sessions"]),
    ("Confusion matrix & accuracy", [
        "Impostor = positive class",
        "Each tested session = one decision (TP, FP, FN, TN)",
        "Accuracy = (TP + TN) / all",
        "Output: best sensitivity and number of sessions"]),
]


def keep_only_new_slide(prs: Presentation, layout_name: str):
    """Drop every existing slide and add one blank slide on the named layout."""
    ids = prs.slides._sldIdLst
    for sld in list(ids):
        prs.part.drop_rel(sld.rId)
        ids.remove(sld)
    layout = next(l for l in prs.slide_layouts if l.name == layout_name)
    return prs.slides.add_slide(layout)


def text(frame, lines: list[tuple[str, int, bool, RGBColor]], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP) -> None:
    frame.clear()
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    for i, (s, size, bold, color) in enumerate(lines):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.alignment = align
        p.space_after = Pt(5)
        r = p.add_run()
        r.text = s
        r.font.size, r.font.bold, r.font.color.rgb, r.font.name = Pt(size), bold, color, "Calibri"


def draw(slide) -> None:
    left, top, width, height, gap = 0.48, 2.95, 1.98, 3.45, 0.35
    head = 1.0
    for i, (title, lines) in enumerate(STEPS):
        x = left + i * (width + gap)
        grp = slide.shapes.add_group_shape()
        grp.name = f"Step {i + 1}"
        body = grp.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(top), Inches(width), Inches(height))
        body.adjustments[0] = 0.06
        body.fill.solid(); body.fill.fore_color.rgb = LIGHT
        body.line.color.rgb = GREEN; body.line.width = Pt(1.5)
        body.shadow.inherit = False
        tf = body.text_frame
        tf.margin_left = tf.margin_right = Inches(0.1)
        tf.margin_top = Inches(head + 0.12)
        text(tf, [("• " + s, 11, False, DARK) for s in lines])
        cap = grp.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(top), Inches(width), Inches(head))
        cap.adjustments[0] = 0.15
        cap.fill.solid(); cap.fill.fore_color.rgb = GREEN
        cap.line.fill.background()
        cap.shadow.inherit = False
        cap.text_frame.margin_left = cap.text_frame.margin_right = Inches(0.08)
        text(cap.text_frame, [(str(i + 1), 12, True, WHITE), (title, 13, True, WHITE)],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        cap.text_frame.paragraphs[0].space_after = Pt(0)
        if i < len(STEPS) - 1:
            arrow = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x + width + 0.05), Inches(top + height / 2 - 0.2),
                                           Inches(gap - 0.1), Inches(0.4))
            arrow.name = f"Arrow {i + 1}"
            arrow.fill.solid(); arrow.fill.fore_color.rgb = GREEN
            arrow.line.fill.background()
            arrow.shadow.inherit = False


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, default=here.parents[1] / "paper/manuscript/Copy of THESIS PROPOSAL.pptx")
    ap.add_argument("--out", type=Path, default=here / "process_overview.pptx")
    args = ap.parse_args()
    prs = Presentation(args.template)
    slide = keep_only_new_slide(prs, "Chapter Intro")
    for ph in list(slide.placeholders):
        if ph.placeholder_format.type != 1:  # keep only the title
            ph._element.getparent().remove(ph._element)
    title = slide.shapes.title
    title.left, title.top, title.width, title.height = Inches(0.48), Inches(1.44), Inches(8.89), Inches(0.88)
    title.text = "Process Overview"
    r = slide.shapes.title.text_frame.paragraphs[0].runs[0]
    r.font.name, r.font.bold, r.font.size = "Garamond", True, Pt(40)
    sub = slide.shapes.add_textbox(Inches(0.48), Inches(2.32), Inches(11.3), Inches(0.45))
    text(sub.text_frame, [("From raw mouse data to the confusion matrix", 18, False, GREEN)])
    draw(slide)
    prs.save(args.out)
    print(f"1 slide, {len(STEPS)} steps -> {args.out}")


if __name__ == "__main__":
    main()
