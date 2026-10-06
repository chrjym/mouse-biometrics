# Adviser Conversation Log

This file is empty for now — fill it in as you go. Claude reads this file whenever it helps with
your thesis, so keeping it current means Claude always knows the latest direction your adviser
has approved or pushed back on.

**How to update this file:** just tell Claude "add this to my adviser log" and paste what
was discussed, or paste a saved chat/email transcript with your adviser, and Claude will
summarize it into an entry below. Newest entries should go on top.

Suggested format per entry:

```
## [YYYY-MM-DD] — Meeting/message topic
**Context:** what was discussed / what you brought to your adviser
**Feedback:** what your adviser said, flagged, or asked you to change
**Decisions:** what you and your adviser agreed to do going forward
**Open questions:** anything still unresolved
```

---

## [2026-08-31] — Scope narrowing: user mannerisms, short mouse signals & tentative title

**Context:** Guidance on narrowing down the operational scope of the study and establishing the formal thesis direction.

**Feedback:** Adviser advised focusing capture directly on the distinct behavioral mannerisms/habits of users (*"Mannerisms ti users latta ngarud ti i-capture yun"*), emphasizing that comparisons should be performed on **short mouse signals/trajectories** (*"Short signals ta mouse ta isu ti i-compare u"*) rather than prolonged or unbounded sessions.

**Decisions:**
- Narrow the operational scope to extracting behavioral mannerisms from short mouse trajectory signals.
- Adopted tentative thesis title: **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication"**.

**Open questions:**
- Operational definition of a "short signal" (e.g., stroke-level segmentation, point-to-point movements between clicks, or sub-second trajectory windows).
- Specific mannerisms / behavioral markers (e.g., sub-movement corrections, discrete curvature habits, stroke straightness) to prioritize for short-signal fingerprinting.

---

## [2026-08-28] — Gap identification & adviser's request for a measurement/comparison survey

**Context:** Presented the RRL gap analysis to the adviser, framed as a 4-phase evolution of
mouse-dynamics authentication literature (Phase 1: early feasibility studies, 2003–2004 →
Phase 2: classical mouse-dynamics biometrics, 2007–2011 → Phase 3: continuous authentication &
geometric features, 2012–2014 → Phase 4: machine learning & deep learning, 2018–2022), plus a
gap table showing that existing work either uses simplified/approximate curvature formulas
instead of rigorous differential geometry, relies on curve-fitting or autoregressive models
instead of measuring geometry directly, uses other similarity measures instead of Fréchet
distance for comparing whole paths, treats global/area-based descriptors as noisy and prone to
ignoring motor pauses, or sacrifices interpretability for learned embeddings (deep learning).

Proposed the thesis's core contribution based on this gap: measuring the shape of a single
mouse movement (from a defined start point to a defined end point) using closed-form local
descriptors — chord deviation, discrete Menger curvature, and straightness ratio — plus a
supplementary global descriptor (convex hull), each computed with explicit safeguards against
its own documented mathematical failure modes. The resulting shape profile is compared against
an enrolled baseline using Fréchet distance, feeding a continuous, per-action trust score that
keeps every authentication decision traceable to a specific geometric property.

**Feedback:** Adviser asked for the full list of measurements/features researchers use for
mouse dynamics, each with a description, and — specifically — how researchers compare
signatures/profiles across samples (i.e., not just what is measured, but what
comparison/matching method is used). Adviser wants the analysis centered on the *differences*
between these measurement and comparison approaches, not just a list.

**Decisions:** 

**Open questions:**
- Whether the adviser wants this organized primarily by descriptor type, by comparison method,
  or as a combined measurement-to-comparison mapping.
- Whether the thesis's own proposed descriptors (chord deviation, Menger curvature,
  straightness ratio, convex hull, Fréchet distance) should be included in the same comparison
  table as the reviewed literature, or presented separately as the contribution once the survey
  is complete.