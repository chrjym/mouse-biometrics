# Study Timeline and Guidelines

Working plan for **"Measuring Behavioral Fingerprints of Users in Mouse Trajectories for Continuous Authentication."**
Last updated: 2026-10-11. Tick boxes as work is done and move finished phases into "Completed".

**Main point (group decision, 2026-10-11):** the thesis stays **geometric**. User mannerisms are measured from the shape of short mouse strokes with closed-form geometric descriptors and the discrete Fréchet distance. Velocity and timing appear only as a comparison or a limitation.

**Citation rule:** every reference must be from **2021–2026** and checked online (DOI or publisher page) before it is cited. Several entries in `paper/references/rrl-candidate-papers.md` could not be verified (see Phase 1).

---

## Completed

| Date | Milestone | Where |
|---|---|---|
| 2026-08-28 | Repo started; gap analysis presented to adviser | `paper/references/adviser-log.md` |
| 2026-08-31 | Scope narrowed to mannerisms in **short** mouse signals; tentative title adopted | adviser log |
| 2026-09-07 → 21 | Weekly literature checker adds candidate papers | `paper/references/new-candidates.md` |
| 2026-09-11 | Candidate RRL and pipeline spec | `paper/references/rrl-candidate-papers.md` |
| 2026-09-26 | Writing auditor and cited background draft | `paper/tools/audit_writing.py`, `background_pure_paragraphs.md` |
| 2026-09-27 → 10-03 | Datasets extracted; first-movement capture; per-user plots | git history (`3e0861e`, `45413a1`) |
| 2026-10-06 → 07 | 1-second-chunk prototype; concave hull vs One-Class SVM benchmark | git history (`069277b`) |
| 2026-10-08 | EARL pipeline 01–08: pause chunks, DTW matching, threshold, sweep, notebook | `experiment_earl/src/` |
| 2026-10-08 | Adviser: use **all** Balabit data (training + test, folder = owner) | adviser log |
| 2026-10-08 | Scripts 09–13: hull, One-Class SVM and DTW anomaly tests (FRR/FAR/EER); enrollment sweep | `experiment_earl/src/09–13` |
| 2026-10-11 | Chapter 3 Methodology drafted, with theoretical framework and 2021–2026 references | Claude Docs: Chapter 3 Methodology |

### Results so far (baselines for the geometric method)

| Method | What it compares | EER (3 legit + 2 impostors, 20 draws) |
|---|---|---|
| Concave hull | Stroke end points | 43.8% |
| DTW library matching | Normalized stroke shape | 43.7% |
| One-Class SVM (6 features) | Shape + speed/duration | 29.6% |

- Shape-only nearest-match does not separate users: about 75–99% of strokes match some stored stroke, for genuine and impostor users alike.
- **Diagnosis:** the problem is the "match any stored stroke" design, not geometry itself. Asgarov (2026) reaches AUC 0.793 / EER 26.4% on Balabit with **geometry only** (path signature + differential geometry), modelled as a per-window distribution.

---

## Phase 1: Clean the references (do first)

Goal: no unverifiable citation reaches the adviser.

- [ ] Remove or replace these RRL entries, which could not be verified or are misattributed:
  - [ ] #11 Djioua & Plamondon (2019), mouse strokes: not found
  - [ ] #13 "IEEE / ACM Biometrics Research Group" (2023): no real authors
  - [ ] #15 Breier, Hou & Bátorová (2021): title actually belongs to Chong et al., IEEE SPW 2018
  - [ ] #16 Fitts' law motor residuals (2021): authors and venue differ between files
  - [ ] Song et al., TIFS 2022 (scene-irrelated mouse dynamics): not found
  - [ ] Antal & Fejér, *Applied Sciences* 2022 (EfficientNet): not found in that journal
- [ ] Fix #5 Asgarov (2026): pages are **13–27**, not 11–22
- [ ] Fix SapiMouse pages: **61–66** (DBLP), not 273–278
- [ ] Update `background_pure_paragraphs.md` so it cites only verified sources
- [ ] Find a verified 2021–2026 source for: discrete Fréchet distance, concave hull algorithm
- [ ] Find the LNCS volume and pages of Yamanaka et al. (INTERACT 2021)

**Done when:** every citation in `paper/` has a working DOI or publisher link and a year from 2021–2026.

## Phase 2: Adviser check-in

Goal: approval of the geometric method before building it.

- [ ] Present the baseline table above and the diagnosis
- [ ] Ask: is the redesign (window-level geometric features + Fréchet against prototypes) acceptable?
- [ ] Ask: may foundational theories (Fitts 1954, Flash & Hogan 1985) be cited as exceptions to the 2021–2026 rule?
- [ ] Ask: is crediting test sessions to the folder owner acceptable, given Balabit's labels mark some as impostors?
- [ ] Log the answers at the top of `paper/references/adviser-log.md`

**Done when:** the adviser log has a dated entry answering all three questions.

## Phase 3: Build the geometric method

Goal: one new experiment that uses the same protocol as scripts 10–12, so EERs are directly comparable.

- [ ] **Script 14, geometric features per window**
  - [ ] Closed-form descriptors per stroke: straightness, chord deviation, discrete (Menger) curvature, at several smoothing scales
  - [ ] Path signature (lead-lag, level 3) per window (`iisignature`)
  - [ ] One-class model (Mahalanobis and One-Class SVM) on window vectors
  - [ ] Windows, enrollment, draws and FRR/FAR/EER exactly as in scripts 10–12
- [ ] **Script 15, discrete Fréchet against user prototypes**
  - [ ] Prototype strokes per user: one medoid per movement-direction group
  - [ ] Score = mean Fréchet distance to the nearest prototype over a 30-stroke window
  - [ ] Same EER protocol
- [ ] **Comparison run:** Fréchet vs DTW in the old library-matching setup (answers the RRL question about warping)
- [ ] **Ablations:** descriptors only, signature only, both; one feature left out at a time
- [ ] Add every new setting to `experiment_earl/config.yaml` and `CONFIG.md`; update `CLAUDE.md` and `experiment_earl/README.md`

**Done when:** one table holds the EER of hull, DTW, SVM, geometric features and Fréchet, as mean ± std over 20 draws.

## Phase 4: Results chapter (Chapter 4)

- [ ] Threshold sweep results (scripts 06 and the notebook)
- [ ] Anomaly-test comparison: all methods, overall and per user
- [ ] Enrollment sweep (1–4 sessions)
- [ ] Ablation results for the geometric features
- [ ] Figures: EER bar chart by method, per-user heatmap, ROC curves
- [ ] Test each hypothesis (H1–H4 in Chapter 3) and state supported or not supported

## Phase 5: Update earlier chapters

- [ ] Chapter 3: add scripts 14–15 as the main method; DTW and hull become baselines
- [ ] Chapter 1: align research questions and scope with the geometric method
- [ ] Chapter 2 (RRL): only verified 2021–2026 sources
- [ ] Run `paper/tools/audit_writing.py` on every chapter draft

## Phase 6: Conclusion and finalization

- [ ] Chapter 5: conclusions, limitations, recommendations
- [ ] Final reference check (Phase 1 rules again)
- [ ] Update `README.md`, which still describes the deleted `experiments/` folder
- [ ] Adviser review and revisions

---

## Proposed schedule

No deadlines have been set yet. Fill in the actual dates once the adviser or the department gives them.

| Phase | Proposed length | Start | Finish |
|---|---|---|---|
| 1. Clean references | 2–3 days | | |
| 2. Adviser check-in | 1 meeting | | |
| 3. Geometric method | 1–2 weeks | | |
| 4. Results chapter | 1 week | | |
| 5. Update chapters | 1 week | | |
| 6. Conclusion and finalization | 1–2 weeks | | |

## Ground rules

1. Geometry is the main point; kinematics only as comparison or limitation.
2. References from 2021–2026, each checked online before it is cited.
3. Every experiment uses the same draws, windows and EER protocol, so results stay comparable.
4. Settings go in `config.yaml`, never hard-coded; each config change gets its own run folder.
5. Record adviser feedback in the adviser log the same day.
6. Commit after every finished change; commit messages contain no names.
