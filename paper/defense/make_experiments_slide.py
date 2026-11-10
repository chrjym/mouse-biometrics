#!/usr/bin/env python3
"""One-slide deck: the two experiments (best sensitivity, best number of sessions) side by side, as editable shapes."""
import argparse
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_process_overview import DARK, GREEN, LIGHT, WHITE, keep_only_new_slide, text  # noqa: E402
from make_matching_slide import box, label  # noqa: E402

ROWS = ["Sessions per user (k)", "Sensitivity", "Splits (I x L)", "Best setting"]
EXPERIMENTS = [
    ("Experiment 1", "Best sensitivity", [
        "1",
        "0.01 → 1.00, step 0.01 (100 values)",
        "all four: 1x5, 5x1, 3x2, 2x3",
        "highest accuracy, counts of all four splits added"]),
    ("Experiment 2", "Best number of sessions", [
        "5, 10, 15 … 40",
        "best of Experiment 1, fixed",
        "all four: 1x5, 5x1, 3x2, 2x3",
        "same: highest accuracy, counts of all four splits added"]),
]


def experiment_box(slide, x: float, top: float, w: float, h: float, name: str, goal: str, values: list[str]) -> None:
    box(slide, x, top, w, h, radius=0.05)
    head = box(slide, x, top, w, 0.85, fill=GREEN, line=None, radius=0.12)
    text(head.text_frame, [(name, 13, True, WHITE), (goal, 18, True, WHITE)], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    for p in head.text_frame.paragraphs:
        p.space_after = Pt(0)
    row_h = (h - 0.85 - 0.15) / len(ROWS)
    for i, (key, value) in enumerate(zip(ROWS, values)):
        y = top + 0.95 + i * row_h
        label(slide, x + 0.12, y, 1.55, row_h - 0.05, [(key, 12, True, GREEN)], align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE)
        label(slide, x + 1.7, y, w - 1.82, row_h - 0.05, [(value, 13, False, DARK)], align=PP_ALIGN.LEFT,
              anchor=MSO_ANCHOR.MIDDLE)
        if i:
            ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + 0.12), Inches(y - 0.03),
                                            Inches(x + w - 0.12), Inches(y - 0.03))
            ln.line.color.rgb, ln.line.width = GREEN, Pt(0.75)


def main() -> None:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, required=True, help="the thesis deck .pptx (its layout is reused)")
    ap.add_argument("--out", type=Path, default=here / "two_experiments.pptx")
    args = ap.parse_args()
    prs = Presentation(args.template)
    slide = keep_only_new_slide(prs, "Chapter Intro")
    for ph in list(slide.placeholders):
        if ph.placeholder_format.type != 1:
            ph._element.getparent().remove(ph._element)
    title = slide.shapes.title
    title.left, title.top, title.width, title.height = Inches(0.48), Inches(1.44), Inches(8.89), Inches(0.88)
    title.text = "The Two Experiments"
    r = title.text_frame.paragraphs[0].runs[0]
    r.font.name, r.font.bold, r.font.size = "Garamond", True, Pt(40)

    top, h, w, gap = 2.55, 3.75, 5.0, 1.25
    left = 0.48
    for i, (name, goal, values) in enumerate(EXPERIMENTS):
        experiment_box(slide, left + i * (w + gap), top, w, h, name, goal, values)
    ax = left + w + 0.12
    a = slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(ax), Inches(top + h / 2 - 0.3), Inches(gap - 0.24), Inches(0.6))
    a.fill.solid(); a.fill.fore_color.rgb = GREEN; a.line.fill.background(); a.shadow.inherit = False
    label(slide, ax - 0.1, top + h / 2 - 1.0, gap - 0.04, 0.65, [("best", 11, True, GREEN), ("sensitivity", 11, True, GREEN)])
    label(slide, left, top + h + 0.15, 2 * w + gap, 0.75, [
        ("Graphs: each setting's counts are added to the ones before it (running total). "
         "Confusion matrix of each experiment = total at its last setting.", 12, False, DARK),
        ("Output → best sensitivity and number of sessions, used to build each user's profile.", 12, True, GREEN)],
        align=PP_ALIGN.LEFT)
    prs.save(args.out)
    print(f"1 slide, {len(EXPERIMENTS)} experiments -> {args.out}")


if __name__ == "__main__":
    main()
