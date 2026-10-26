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

## [2026-10-26] — Thesis Consultation v6: experiments 1 and 2 with confusion matrices

**Context:** Consultation sheet `Queries-2.pdf` (whiteboard photo + notes). Earlier scripts for this (`15_best_setting.py`, `16_initial_results.py`) and `Sensitivity Sweep Process and Results.md` were deleted by the group as false.

**Feedback:**
- Experiment 1, User x User x Sensitivity: 1 session, every sensitivity 0.01 … 1.00 in 0.01 steps; two graphs (legitimate user, impostor user), x = sensitivity, y = accuracy (0 bad, 1 good), one line per split. Pick the best-accuracy sensitivity from the CSV and use it in experiment 2.
- Experiment 2, User x Sensitivity x Session: the best sensitivity of experiment 1, sessions 5, 10, … 40; the same two graphs with x = sessions; pick the best from the CSV.
- Splits 1 x 5, 5 x 1, 3 x 2, 2 x 3 (I x L).
- Confusion matrix, positive = impostor: TP = impostor caught, FP = user wrongly blocked, FN = impostor let in, TN = real user accepted. Accuracy = (TP + TN) / (TP + TN + FP + FN). One confusion matrix per graph.

**Decisions (group, same day):**
- Counts are sessions (each tested session is one decision); an impostor's sessions are tested against the legitimate library that passes most of them (the batch rule).
- The counts of every iteration are added to the ones before it until the last iteration; the graphs plot these running totals, and the confusion matrix is the total at the last iteration with all splits added (one per experiment figure).
- The best sensitivity / session count is picked on each point's own counts, all splits added.
- Implemented as section 9 of `experiment_earl/notebooks/earl_simulation.ipynb` (CSV + PNG in `runs/<hash>/experiments/`); section 7 (logic of the deleted 15) removed.

**Open questions:**
- Whether "one confusion matrix per graph" means one per experiment figure (as built) or a separate one for the legitimate and the impostor graph.
- Whether the running total should also drive the best pick (it now uses each point's own counts).

---

## [2026-10-26] — Run the simulation notebook from the Jupyter terminal

**Context:** The simulation notebook (`experiment_earl/notebooks/earl_simulation.ipynb`) was built the same day to replace the scripts.

**Feedback:** In a demonstration, the adviser ran the simulation from a terminal inside the Jupyter server, and suggested running it that way.

**Decisions:**
- Long runs are started from JupyterLab's own terminal (File → New → Terminal) with `nohup .venv/bin/jupyter execute experiment_earl/notebooks/earl_simulation.ipynb > experiment_earl/runs/notebook_run.log 2>&1 &`, so they keep running after the browser tab is closed. Run All in the browser stays for short runs.
- Progress is followed in `runs/batch_log.csv` (one line per finished run), because `jupyter execute` does not show the cells' printed output; steps written to `experiment_earl/notebooks/HOW_TO_RUN.md`.

**Open questions:**
- Whether this is exactly the command the adviser used (the group did not see it); confirm at the next consultation.

---

## [2026-10-26] — Replace the Python scripts with a Jupyter notebook

**Context:** The EARL experiment runs as numbered scripts in `experiment_earl/src/` from the terminal (batch, accuracy, best setting, sweep). Cleanup the same day removed the executed-notebook copies, the PNG output of 08–10 and the cohort / seed-check scripts (old 13–15), and renumbered the sweep to 13–15.

**Feedback:** All Python scripts should be replaced by a Jupyter notebook (`.ipynb`), and every simulation should run in the notebook, not from the terminal.

**Decisions:**
- One new notebook replaces the scripts; `notebooks/session_progression.ipynb` is no longer used.
- All settings are set inside the notebook; it writes CSV outputs only for now (the group writes the figure code later).
- It must run locally, on another machine or on a remote Jupyter server.

**Open questions:**
- Which script stages carry over into the notebook (e.g. the file-based single trial 01–05, the per-chunk PNGs of 06, matched pairs 08, genuine check 09)?
- Whether `config.yaml`, `batch.yaml` and the per-script docs are retired with the scripts.

---

## [2026-10-24] — Sweep concept: best setting per user (18) and confusion-matrix figure

**Context:** Additions to `experiment_earl/SWEEP_CONCEPT.md` (commits `16aa0f77b`, `9b39140cb`, `4127e22b1`), to bring to the adviser. Not adviser feedback yet.

**Feedback:** None yet; to be presented at the next consultation.

**Decisions (as the code stands):**
- **New figure (17):** `confusion_matrices.png`, 2 × 2 matrices per split at sensitivity 0.01, 0.02, 0.05, 0.10 (40 sessions), with counts and the share of each column. The sweep now outputs four figures.
- **Best setting per user (18):** the sweep (16) also keeps one confusion matrix per legitimate user (the user's own test sessions plus every impostor attempt against their library). Each user's 40 test sessions alternate between two halves:
  - **Pick** (even, 20 sessions): choose the setting with the highest balanced accuracy; ties → fewer sessions, then lower sensitivity.
  - **Check** (odd, 20 sessions): score that same setting on sessions it never saw.
- The check-half score is the one to report: the pick score is the best of 4,000 settings and always optimistic. A user is profiled reliably only when the check score stays close to the pick score and clearly above 0.5. The same is done per split by adding its users' counts.
- Reading: library size = sessions needed at registration; sensitivity = verification tolerance.
- **Figures** (run order 16 → 18 → 17): the split's best is an orange star on the heatmap and the accuracy line graph; each user's best is a labelled circle on the heatmap; each panel shows the pick → check balanced accuracy.

**Open questions:**
- Section 8 ("Why no best setting is picked") still contradicts section 10; which framing should the thesis use?
- Is a pick/check split of one seed's sessions enough, or should the frozen best setting also be tested on held-out seeds (e.g. 946–955)?
- The figures table in the concept lacks the best-setting star on the accuracy line graph.

---

## [2026-10-24] — Sweep: seed (RNG) dependence and how the confusion matrix is counted

**Context:** Group clarification of the sensitivity sweep (`experiment_earl/src/16_sweep_sensitivity.py`, `sweep.yaml`, run `19399f`), to bring to the adviser. Not adviser feedback yet.

**Feedback:** None yet; to be presented at the next consultation.

**Decisions (as the code stands):**
- **Seed / RNG:** the whole sweep rests on one seed (`seed: 945` in `sweep.yaml`). It drives the two random draws of Earl's idea (#3 random users, #4 random sessions): `Random(seed)` picks the legitimate and impostor users (no overlap), and `Random(f"{seed}-{user}")` shuffles each user's sessions once. DTW distances and the sensitivity cut are deterministic, so the same seed gives the same results.
- Each split re-draws from the same seed with a different `n_legitimate`, so the four splits (5L/1I, 1L/5I, 3L/2I, 2L/3I) contain different users; a user's session order is the same in every split.
- Random sessions match Earl's idea #4 (group decision 2026-10-24): each user's sessions are drawn at random from the seed, and the draw stays the same across library sizes (library k+1 = library k plus one session, as decided 2026-10-12).
- Sweep vs `EARL_IDEA.md`: same as #1 (Balabit only), #2 (chunked shapes), #3 (random users) and #4 (random sessions). Different from #5–#8:
  - #5 matching: a chunk matches when its best DTW distance to the library is ≤ sensitivity; a session passes when ≥ `match_shape_ratio` of its chunks match.
  - #6 threshold: in Earl's idea it is the result (matched impostors / total impostors); in the sweep, sensitivity (the renamed threshold, 2026-10-14) is the DTW tolerance being varied (0.01–1.00), and the result is a confusion matrix (FAR, FRR, accuracy).
  - Who is tested: Earl's idea tests impostors only; the sweep also tests each legitimate user's own unseen sessions.
  - #7 bar graph (impostors matched vs impostors): replaced by balanced accuracy and FAR/FRR vs sensitivity line graphs.
  - #8 heatmap (sessions × legitimate users, colour = threshold): replaced by sessions × sensitivity heatmaps, one per fixed split (5L/1I, 1L/5I, 3L/2I, 2L/3I).
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