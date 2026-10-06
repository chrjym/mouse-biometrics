---
name: mouse-biometrics-thesis
description: Use this skill for ANY work on the thesis "Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication" (Mouse Dynamics Behavioral Biometrics) — drafting or revising thesis chapters (Introduction, RRL, Methodology, Results, Discussion), writing or checking citations, identifying literature gaps, prepping for or logging adviser meetings, and tracking adviser feedback/decisions. Trigger this whenever the user mentions their thesis, RRL, related literature, mouse dynamics, behavioral biometrics, continuous authentication, user mannerisms / behavioral fingerprints, their thesis adviser, or asks Claude to remember/apply adviser feedback — even if they don't explicitly say "use the skill." Always check paper/references/adviser-log.md for the latest adviser guidance before giving thesis direction, and check paper/references/annotated-bibliography.md before citing or discussing related literature.
---

# Mouse Dynamics Behavioral Biometrics Thesis Assistant

Supports work on the thesis **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication"** — grounded in the group's compiled Review of Related Literature (RRL) and an ongoing log of adviser feedback. Focuses on capturing user mannerisms from short mouse signals/trajectories.

## What this skill contains

- `paper/references/annotated-bibliography.md` — ~46 sources compiled by the thesis group (4 members),
  organized by theme (angle/curvature methods, deep learning, multimodal fusion, evaluation
  methodology, adversarial robustness, alternative modalities, deployment constraints, and
  geometric/spatial-feature-focused work). Each entry has a summary, strengths, and
  limitations/gaps as logged by the group.
- `paper/references/measurement-comparison-survey.md` — consolidated survey of mouse dynamics measurements,
  feature descriptions, profile comparison methods, and decision mechanisms across the literature, contrasting
  them directly against our proposed closed-form geometric approach.
- `paper/references/literature-sources.md` — options, access methods, status, and instructions for querying academic APIs (arXiv, OpenAlex, Semantic Scholar, CORE, Crossref, etc.).
- `paper/references/example-rrl-fetch.py` — automated fetch and cross-checking script for retrieving candidate literature from free/no-key APIs and comparing against the annotated bibliography.
- `paper/references/pipeline.md` — end-to-end methodology pipeline specification: short-signal segmentation, closed-form geometric mannerism extraction (Menger curvature, chord deviation, straightness ratio, convex hull), Discrete Fréchet distance comparison, and continuous dynamic trust scoring.
- `paper/references/adviser-log.md` — running log of adviser meetings/feedback. Always check it before
  giving thesis direction to ensure alignment with adviser decisions and requests.

## How to use this skill

**Before drafting or revising any thesis content:**
1. Read `paper/references/adviser-log.md` first. If it has entries, treat the most recent decisions
   as binding constraints — don't suggest directions the adviser already pushed back on, and
   flag if a request conflicts with a logged decision.
2. If relevant, read `paper/references/annotated-bibliography.md` for the specific theme in play
   (see its table of contents) rather than skimming the whole file each time.

**When checking for new literature / candidate papers ("any new papers on this," "check for updates"):**
1. Reference `paper/references/literature-sources.md` and run or inspect the output of `paper/references/example-rrl-fetch.py`.
2. Cross-check each candidate's title/DOI against `paper/references/annotated-bibliography.md` (only genuinely new ones matter).
3. Present new candidates to the user for their review — do not auto-add anything to the annotated bibliography without user confirmation.

**When drafting RRL / Related Literature sections:**
- Pull from the annotated bibliography, but always paraphrase into the thesis's own voice —
  don't lift the summary sentences verbatim, they're notes, not citable prose.
- Point out where two entries conflict or where a gap in the literature (noted under
  "Limitations" for several sources) could become the thesis's own contribution or justification.
- Go back to the original DOI/URL for exact figures/quotes when precision matters — the
  annotated bibliography is a working summary, not the source of record.

**When logging a new adviser conversation:**
- The user may paste a raw chat/email transcript or just describe what was said.
- Summarize it into the log's entry format (Context / Feedback / Decisions / Open questions),
  add it to the **top** of `paper/references/adviser-log.md`, and confirm back to the user in a
  couple of sentences what got logged.
- Don't editorialize or add feedback the adviser didn't give — this log is meant to be an
  accurate record, not Claude's own opinion.

**When prepping for an upcoming adviser meeting:**
- Check the adviser log's "Open questions" from the most recent entries and surface them.
- Check for any thesis work done since the last logged meeting that the adviser hasn't
  weighed in on yet, and suggest bringing it up.

## Keeping this skill current

This skill is meant to grow with the thesis. If the user shares more RRL sources, new
adviser meeting notes, or later a Methodology/Results draft they want Claude to always have
context on, add them into `paper/references/` (new files if the content is a different kind of
material, e.g. `paper/references/methodology-draft.md`) and update this SKILL.md's description if
the scope changes.
