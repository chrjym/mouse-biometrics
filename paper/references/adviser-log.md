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

## [2026-10-24] — Sweep: seed (RNG) dependence and how the confusion matrix is counted

**Context:** Group clarification of the sensitivity sweep (`experiment_earl/src/16_sweep_sensitivity.py`, `sweep.yaml`, run `19399f`), to bring to the adviser. Not adviser feedback yet.

**Feedback:** None yet; to be presented at the next consultation.

**Decisions (as the code stands):**
- **Seed / RNG:** the whole sweep rests on one seed (`seed: 945` in `sweep.yaml`). It drives the two random draws of Earl's idea (#3 random users, #4 random sessions): `Random(seed)` picks the legitimate and impostor users (no overlap), and `Random(f"{seed}-{user}")` shuffles each user's sessions once. DTW distances and the sensitivity cut are deterministic, so the same seed gives the same results.
- Each split re-draws from the same seed with a different `n_legitimate`, so the four splits (5L/1I, 1L/5I, 3L/2I, 2L/3I) contain different users; a user's session order is the same in every split.
- Differences from `EARL_EXECUTION_PLAN.md`: the plan (step 4.2/4.4) averages `n_trials` draws with different seeds and reports mean ± SD; the sweep uses a single draw. Sessions are nested (library k+1 = library k plus one session; group decision 2026-10-12) instead of re-picked each time.
- **Confusion matrix:** one full 2×2 matrix per (split, library size 1–40, sensitivity 0.01–1.00), 16,000 in `confusion.csv`. Positive class = impostor: TP = impostor rejected, FN = impostor accepted (FAR), FP = legitimate rejected (FRR), TN = legitimate accepted.
- **What is appended:** every (test session, profile) attempt is one entry. Legitimate: each user's last 40 sessions against their own library only. Impostor: each impostor's first 40 sessions against every legitimate library as separate attempts (40 × L entries). Library sizes are a running minimum over the same distances and sensitivities are cuts on the same saved distances, so neither adds new tests. The four split files are concatenated at the end. A user-level matrix (`users_*`) counts a user as accepted when ≥ `match_session_ratio` of their attempts pass.
- Caveat: the script reuses existing `sweep/parts/*.csv` files (resume), and the folder hash depends on the config, not the code; delete `parts/` before rerunning after a code change.

**Open questions:**
- Should the sweep run over several seeds (e.g. 945–954) and report mean ± SD per cell, as in Earl's plan? This overlaps the held-out-seed check (tune on one seed, test on others), which on 2026-10-19 fell to chance.
- Is impostor = positive class the convention the adviser wants for FAR/FRR?
- The sweep's `labels_file` filter (drops `is_illegal = 1` sessions) conflicts with the 2026-10-08 "no labels" decision; needs adviser sign-off.

---

## [2026-10-14] — New experiment pipeline: experiments E_k, find the sensitivity, find the sessions

**Context:** Consultation on the EARL shape-matching experiment; notes and whiteboard photo in `Queries.pdf` (random variables: user, session, sensitivity, data points; experiments: 1. move stroke, 2. user × user × sensitivity, 3. user × session × sensitivity; seed = 41 on the board).

**Feedback:**
- Keep DTW as the matching method throughout; keep the chunking as is. Drop the One-Class SVM entirely (remove all related functions).
- Rename every "threshold" in the scripts and experiment to **sensitivity**.
- Merge Balabit `training_files` and `test_files` into one folder per user.
- New experiment design: from a seeded draw of n users, experiment E_k has k legitimate users and the direct-opposite n − k impostors (n = 5: E1 = 1 + 4, E2 = 2 + 3, …).
- **Find the sensitivity** (user × user × sensitivity): sensitivity = `dtw_tolerance`, 0.2 to 1.0 in steps of 0.2 (0 = unique, 1 = similar on the board); other config settings may become sensitivities later. Line graphs, y = accuracy, x = impostor / legitimate users, separate graphs for legitimate and impostor, one line per sensitivity.
- **Find the sessions** (user × session × sensitivity): 2, 4, … 10 sessions per user at the sensitivity found above; same graphs, one line per session count.
- Pipeline: raw → RNG (legitimate users, impostor users, sessions) → mouse strokes (chunk shapes) → user × user × sensitivity → user × session × sensitivity → sensitivity (formerly threshold) → heatmap.

**Decisions:**
- Implemented as `experiment_earl/src/09_find_sensitivity.py` and `10_find_session.py`; data merged into `experiment_earl/datasets/balabit/users/`. The hull, One-Class SVM and DTW anomaly tests and the enroll sweep (old scripts 09–13) were removed along with the OCSVM (group decision).
- Accuracy (group decision): legitimate = share of legitimate users whose own unseen sessions pass their own profile; impostor = share of impostors rejected by every legitimate profile. The chosen sensitivity per E_k maximizes the mean of the two.
- Changed the same day (group decision): the direct-opposite split is dropped. The legitimate/impostor counts of each experiment are set by hand in `config.yaml` (`experiments: [[L, I], ...]`); the seed still picks which users and sessions.
- Later the same day (group decision): 09 and 10 have no settings of their own any more. They use the main configuration (`seed`, `n_legitimate`, `n_impostor`, `sessions_per_user`, and `sensitivity`, which is the renamed `dtw_tolerance`); a different sensitivity is tried by editing `sensitivity` and rerunning. Graphs show accuracy per user.
- First run (`oct14_test1`, still with the direct-opposite split): at every sensitivity 0.2–1.0 and every session count 2–10, all legitimate users pass and all impostors get through (heatmap all 1.0). Users only start to differ around `dtw_tolerance` 0.03–0.05.

**Open questions:**
- The 0.2–1.0 grid saturates (0.15 already matched ~99% of strokes). Ask the adviser whether to use a finer grid (e.g. 0.01–0.05), or to read "sensitivity 0–1" as a scale mapped onto the tolerance.
- The board's "seed = 41": the config still uses the group's own seed. Confirm whether 41 should be used.

---

## [2026-10-08] — Use all the data in the experiments

**Context:** The EARL shape-matching experiment (`experiment_earl/`) used only Balabit's `training_files` to build and compare user profiles; `test_files` were used only in a separate FAR/FRR/EER evaluation (`09_evaluate_test.py`). Relayed by a group member.

**Feedback:** Adviser instructed: use all the data and run the experiments on all of it.

**Decisions:**
- Balabit `test_files` must be part of the experiments, not only training files.
- "All data" means all of Balabit (training + test files), not SapiMouse.
- Group decision: use the raw data only. A session belongs to the user whose folder it is in, for training and test files alike (1,676 sessions, 114–253 per user). Balabit's `public_labels.csv` is not used. A label-based version (genuine/impostor/unlabeled test sessions, and the FAR/FRR/EER test evaluation built on it) was tried the same day and dropped.

**Open questions:**
- Balabit published the test folders as "sessions claimed to be this user", and its public labels mark about half of the labeled ones as someone else. If the adviser asks how the folder-owner rule handles this, the label-based version is in git history (commits `a5a170c`–`35781ab`).

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