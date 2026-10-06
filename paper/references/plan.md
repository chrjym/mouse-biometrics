# Thesis Task Plan: New Literature Checker & Candidate Tracker

**Task:** Build a runnable literature checker querying arXiv, OpenAlex, Semantic Scholar, and SerpApi Google Scholar, deduplicating across sources, cross-checking against `references/annotated-bibliography.md`, and prepending new candidates to `references/new-candidates.md`.
**Status:** Done
**Completed Date:** 2026-08-31

## Deliverables & Actions Taken
- [x] Read `references/example-rrl-fetch.py`, `references/literature-sources.md`, and `references/annotated-bibliography.md`.
- [x] Transformed `example-rrl-fetch.py` into a runnable CLI module supporting configurable queries (defaulting to `"mouse dynamics" "authentication"` and `"curvature" "mouse trajectory"`).
- [x] Implemented multi-source fetchers for arXiv, OpenAlex, Semantic Scholar, and optional Google Scholar via SerpApi (with graceful fallback if `SERPAPI_KEY` is not provided).
- [x] Built cross-source deduplication via normalized title similarity (Jaccard + SequenceMatcher) and DOI normalization.
- [x] Built ground-truth extractor from `annotated-bibliography.md` to filter out all known titles, DOIs, and arXiv identifiers.
- [x] Implemented incremental history-preserving prepending in `references/new-candidates.md`.
- [x] Created GitHub Actions cron workflow `.github/workflows/literature-checker.yml` scheduled weekly and callable on-demand via `workflow_dispatch`.
- [x] Preserved `references/annotated-bibliography.md` completely unmodified.

---

# Thesis Task Plan: Measurement & Comparison Survey

**Task:** Synthesize a comprehensive measurement and profile comparison survey for mouse dynamics behavioral biometrics based on adviser feedback dated 2026-08-28.
**Status:** Done
**Completed Date:** 2026-08-28

## Deliverables & Actions Taken
- [x] Read and analyzed all ~46 sources in [annotated-bibliography.md]
- [x] Extracted the full inventory of measurement descriptors (kinematic, temporal/clickstream, angle/directional, classical/differential curve geometry, spectral, deep/learned, sensor-augmented).
- [x] Extracted and contrasted all profile matching/comparison mechanisms (vector distance metrics, supervised classifiers, one-class anomaly detectors, deep latent embeddings, elastic curve alignment).
- [x] Built consolidated deduplicated comparison survey at [measurement-comparison-survey.md] focusing on decision mechanisms ("how systems decide same user or not").
- [x] Added visually distinct closing section for "Our Proposed Approach" (closed-form chord deviation, discrete Menger curvature, straightness ratio, convex hull + Fréchet distance + continuous trust score).
- [x] Updated [SKILL.md]to index the new survey document.
