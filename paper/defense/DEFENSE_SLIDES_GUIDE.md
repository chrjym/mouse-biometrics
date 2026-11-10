# Defense Slides Guide: Raw Data to Confusion Matrix

What to put on each slide, which figure or table to use, and what to say. It covers only **raw data → strokes → DTW matching → Experiments 1 and 2 → confusion matrix**. The hulls, Euclidean distance and FAR/FRR/EER are left to the other members.

**Where every number comes from.** All numbers here were checked against the generated data, not copied from the manuscript alone:

| Source | What it gives |
|---|---|
| `paper/manuscript/All_Manuscript.pdf` | Chapter III (Methodology) and Chapter IV (Results) text, Tables 1–4 |
| `experiment_earl/datasets/balabit/users/` + `public_labels.csv` | Table 1 (1,676 sessions, 405 illegal, 1,271 used): recounted, matches |
| `experiment_earl/runs/a6e6f7/strokes/all_strokes.csv` | Table 2 (109,948 strokes, 106,320 move / 3,628 drag): recounted, matches. Cutting into strokes does not depend on the seed, so it holds for run `19399f` too |
| `experiment_earl/runs/19399f/experiments/` (seed 945) | Experiments 1 and 2: `exp1_overall.csv`, `exp1_points.csv`, `exp2_overall.csv`, `exp2_points.csv`, the confusion CSVs and the figures. Tables 3 and 4 match these files exactly |
| `experiment_earl/runs/19399f/<split>_0.05_<k>/results/accuracy.csv` | Which users were legitimate or impostor in each split, and which sessions passed (backup slide) |

Every figure the slides need is copied into `paper/defense/figures/`:

| File | Use | Origin |
|---|---|---|
| `fig_m1_segmentation.png` | Methodology: raw session → strokes → normalized strokes | **New**, drawn from real data: user29 `session_0136325499`, using the notebook's own stroke export (`runs/a6e6f7/strokes/user29/`). Script: `paper/defense/make_segmentation_figure.py` |
| `exp1_graph.png` | Experiment 1 accuracy curves (manuscript Figure 1) | `runs/19399f/experiments/` |
| `exp1_confusion.png` | Experiment 1 confusion matrix (manuscript Figure 2) | same |
| `exp2_graph.png` | Experiment 2 accuracy curves (manuscript Figure 3) | same |
| `exp2_confusion.png` | Experiment 2 confusion matrix (manuscript Figure 4) | same |
| `process_overview_diagram.png` | Slide M1 flow, **transparent PNG** (no title, logo or background) | `make_visual_pngs.py` |
| `matching_dtw_diagram.png` | Slide M4 DTW matching diagram, **transparent PNG**, compact with short labels (10.25 × 3.9 in) | `make_matching_png.py --experiment experiment_earl`. The image has no source line, so say it: *"The strokes are real user29 strokes. The bars are from run 19399f, split 1x5, sensitivity 0.05, one session: user29's own session matched 19 of 66 strokes against its own library; impostor user16 matched 9 of 65 against user9's library, its best."* |
| `two_experiments_diagram.png` | Slide M6 two experiments, **transparent PNG**, compact with short labels (9.54 × 2.96 in) | `make_visual_pngs.py`. The image has no footer, so say it: *"Both experiments use all four splits (1x5, 5x1, 3x2, 2x3) and add their counts together; the best setting has the highest accuracy. The graphs add each setting's counts to the ones before it, and each confusion matrix is the total at the last setting. The output, the best sensitivity and number of sessions, builds each user's profile."* |

The transparent PNGs (300 dpi) are meant to be dropped onto your own slides. They are drawn for the deck's white background: the text outside the boxes is dark and won't show on a dark slide. The `.pptx` versions (`process_overview.pptx`, `matching_dtw.pptx`, `two_experiments.pptx`) have the same content as editable shapes.

---

## ⚠ Confirm these with me before the slides are final

I found these while checking the manuscript against the data. **I have not changed the manuscript.** The slide text below follows the data. Tell me which ones you want fixed in the manuscript too.

1. **Chapter IV, the paragraph after Table 3, has the two groups swapped.** It says *"all 11 legitimate sessions were rejected, but 6 out of 11 impostor sessions were wrongly accepted."* The data (Table 3 itself) says the reverse: **all 11 impostor sessions were rejected** (TP 11, FN 0), and **6 of the 11 legitimate sessions were wrongly rejected** (FP 6, TN 5). The later sentence *"The cost of this choice is that 6 of the 11 legitimate sessions are wrongly rejected"* is correct.
2. **Same paragraph: "The confusion matrix in Figure 1"** should be **Figure 2**.
3. **"The researchers used 0.05 for four reasons"**: only three reasons follow (highest/balanced accuracy, 1.00 lets all impostors in, impostors have priority).
4. **The closing paragraph of Data Preprocessing and Segmentation does not match the data.** It says *"…splits from 5 legitimate x 1 impostor, showing 25 enrolled sessions yielding to 125 legitimate sessions and 25 impostor sessions for a total of 150 registered sessions."*
   - With the I x L naming used in the tables and figures, **5x1 = 5 impostors, 1 legitimate user (user29)**. The split with 5 legitimate users and 1 impostor (user16) is **1x5**.
   - At 5 sessions, 1x5 tests 25 legitimate and 5 impostor sessions (Table 4: 1+24 and 0+5). Over all four splits Experiment 2 tests 55 legitimate and 55 impostor sessions at 5 sessions. The numbers 125 and 150 appear nowhere in the outputs.
   - 5x1 has the **lowest** accuracy at 5 sessions (0.27), not the best values.
   - This paragraph is the bridge into the hull section, so the members doing the hulls should check it too.
5. **Table 2's caption says "(medians per stroke)"**, but the table has no medians. From the data, the median stroke has 17 points and lasts 1.51 s if you want to add them; otherwise drop the phrase.
6. **Chapter III, Segmentation**: *"the strokes were organized to not include those with at least 10 movement points"* should be **fewer than 10** (the code keeps strokes with ≥ 10 points). Chapter III also never says that each stroke is **resampled to 64 points** before DTW. The code does this (`resample_n: 64`), and it is why "average distance per point" divides by 64. I included it on the slide because it is part of the actual process.
7. **For the hull members, not my slides:** Chapter III's Feature Extraction paragraph defines **1×5 as "one legitimate user and five impostors"** and says **"5×1 reached its best setting at 0.02 with 25 sessions."** Both contradict Chapter IV and the data (I x L naming; one best setting of 0.05 and 5 sessions over all splits). Chapter IV's hull section also calls the split with five legitimate users and impostor user16 **"5x1"**; under I x L that is **1x5**. Chapter IV also has two tables numbered "Table 4".
8. You mentioned **3 slide categories** but described two (Methodology, Results and Discussion). This guide covers those two. Tell me what the third is.

---

## Category 1: Methodology (raw data → confusion matrix)

### Slide M1: Process overview

- **Visual: ready-made.** `process_overview.pptx` is this slide built on the deck's own "Chapter Intro" layout (MMSU logo, background, Garamond title). The five steps are editable PowerPoint shapes (each step is a group, plus four arrows). Copy the slide into the deck, or select the shapes and paste them onto your own slide. Preview: `figures/process_overview.png`. Rebuild with `make_process_overview.py --template "<deck>.pptx"`.
  `Balabit raw data → Clean & cut into strokes → Normalize strokes → DTW matching (sensitivity, sessions) → Confusion matrix & accuracy`
  No hull/Euclidean boxes are on it. Box 5 says "Output: best sensitivity and number of sessions" without the numbers, so the results stay on the Results slides.
- **On-slide text:**
  - Input: Balabit Mouse Dynamics dataset, 10 users
  - Output of this stage: the best **sensitivity** and **number of sessions** used to build each user's profile
- **Say:** "Before we describe a user's shape, we have to decide how strict the matching is and how many sessions make a profile. This part of the method answers those two questions with two experiments scored by a confusion matrix."

### Slide M2: Data acquisition and organization

- **Table (real rows from `datasets/balabit/users/user29/session_0136325499`):**

  | record timestamp | client timestamp | button | state | x | y |
  |---|---|---|---|---|---|
  | 0.0 | 0.0 | NoButton | Move | 403 | 360 |
  | 0.217 | 0.094 | NoButton | Move | 329 | 501 |
  | 0.217 | 0.218 | NoButton | Move | 332 | 580 |

- **On-slide text:**
  - Balabit Mouse Dynamics Challenge dataset: **10 users, 1,676 sessions**
  - Each record = timestamps, button, state (Move / Drag / Pressed / Released), cursor x, y
  - Sessions organized per user folder; **405 sessions labelled illegal** in the public labels were removed → **1,271 sessions**
- **Say:** "Every session is a stream of cursor records. We keep each session under its owner, and drop the 405 the dataset marks as illegal, so every remaining session belongs to the user it is filed under."

### Slide M3: Preprocessing and segmentation

- **Figure:** `figures/fig_m1_segmentation.png` (full width). Panel (a) is one real session of user29 (692 records, 54 clicks), (b) the same session cut into its 18 strokes, (c) the 18 strokes moved to (0, 0), scaled and resampled.
- **On-slide text (the steps, in order):**
  1. **Clean:** remove missing values, scroll events, invalid coordinates (x = y = 65535); order by time, start at 0 s
  2. **Cut:** a new stroke starts after a **pause > 0.5 s** or a **mouse click**
  3. **Filter:** keep strokes with **≥ 10 points**
  4. **Label:** **drag** if more than half its points are dragging, else **move**
  5. **Normalize:** start point moved to **(0, 0)**, scaled by its **bounding-box diagonal**, resampled to **64 evenly spaced points**
- **Say:** "Normalizing removes where on the screen and how big the movement was, so only the shape remains. This matters because Balabit users have different screens and sampling rates."

### Slide M4: Matching strokes with DTW

- **Visual: ready-made.** `matching_dtw.pptx` (preview `figures/matching_dtw.png`, rebuild with `make_matching_slide.py --template "<deck>.pptx" --experiment experiment_earl`). Editable shapes on the deck's "Chapter Intro" layout:
  - Top row: one tested stroke → compared with every same-type stroke in the library (d₁ … dₙ; a drag stroke crossed out as skipped) → smallest distance ÷ 64 points → diamond "d ≤ sensitivity?" → match / no match. The strokes drawn are real user29 strokes, normalized like the notebook. The distances stay symbolic (no values are invented).
  - Bottom row: session bars with the real counts from run `19399f`, split 1x5, sensitivity 0.05, 1 session: **user29's own session matched 19 of 66 strokes (29%) → accepted**; **impostor user16 matched 9 of 65 (14%) against user9's library (its best) → rejected**, with the 20% line dashed.
- **On-slide text:**
  - **Dynamic Time Warping (DTW)** compares two strokes while allowing one to stretch against the other; stretching limited to **10% of the stroke length**
  - Only strokes of the **same type** (move–move, drag–drag) are compared
  - For each tested stroke: the **smallest DTW distance** to any stroke in the library, **averaged per point**
  - **Stroke matches** if that distance ≤ **sensitivity** (lower sensitivity = stricter)
  - **Session accepted** if **≥ 20%** of its strokes match
- **Say:** "Sensitivity is the tolerance. At 0.01 two strokes must be almost identical; at 1.00 almost anything matches. Experiment 1 finds the right value."

### Slide M5: Profiles, splits and the confusion matrix

- **Table 1, the four splits (I x L = impostors x legitimate users):**

  | Split (I x L) | Impostors | Legitimate users |
  |---|---|---|
  | 1x5 | 1 | 5 |
  | 5x1 | 5 | 1 |
  | 3x2 | 3 | 2 |
  | 2x3 | 2 | 3 |

- **Table 2, the confusion matrix (positive class = impostor):**

  | | Actual impostor | Actual legitimate |
  |---|---|---|
  | **Rejected** | TP (impostor blocked) | FP (legitimate wrongly blocked) |
  | **Accepted** | FN (impostor let in) | TN (legitimate let in) |

- **Formula:** Accuracy = (TP + TN) / (TP + TN + FP + FN)
- **On-slide text:**
  - Each user's sessions are shuffled once into a fixed order (seed 945)
  - **Library** = a legitimate user's first *k* sessions; **legitimate test** = their last *k* sessions (never in the library)
  - **Impostor test** = the impostor's first *k* sessions against every legitimate library; the library that accepts the most is used
  - Every tested session = **one decision**
- **Say:** "We treat catching an impostor as the positive event, because that is what an authentication system exists to do."

### Slide M6: The two experiments

- **Visual: ready-made.** `two_experiments.pptx` (preview `figures/two_experiments.png`, rebuild with `make_experiments_slide.py --template "<deck>.pptx"`): the two boxes below as editable shapes on the deck layout, an arrow labelled "best sensitivity" from Experiment 1 to Experiment 2, and the running-total note and output line at the bottom.

  | | Experiment 1: best sensitivity | Experiment 2: best number of sessions |
  |---|---|---|
  | Sessions per user (*k*) | 1 | 5, 10, 15 … 40 |
  | Sensitivity | 0.01 → 1.00, step 0.01 (100 values) | best of Experiment 1, fixed |
  | Splits | all four | all four |
  | Best setting | highest accuracy, counts of all four splits added | same |

- **On-slide text:** For the graphs, each setting's counts are added to the ones before it (running total), and the confusion matrix of each experiment is the total at its last setting.
- **Say:** "Experiment 1 fixes strictness, Experiment 2 uses it to decide how many sessions a profile needs. Those two values are passed on to the feature extraction."

---

## Category 2: Results and Discussion (raw data → confusion matrix, no hulls)

### Slide R1: Data acquisition result

- **Table:** manuscript Table 1 (Sessions per user), all 10 rows + total. Verified against the dataset:

  | User | Sessions | Illegal removed | Used |
  |---|---|---|---|
  | user7 | 158 | 37 | 121 |
  | user9 | 130 | 43 | 87 |
  | user12 | 240 | 49 | 191 |
  | user15 | 253 | 70 | 183 |
  | user16 | 201 | 38 | 163 |
  | user20 | 114 | 20 | 94 |
  | user21 | 121 | 22 | 99 |
  | user23 | 142 | 33 | 109 |
  | user29 | 124 | 20 | 104 |
  | user35 | 193 | 73 | 120 |
  | **Total** | **1,676** | **405** | **1,271** |

- **On-slide text:** Usable sessions range from **87 (user9)** to **191 (user12)**. Every user must supply the same number of sessions in a run, so the smallest pool limits profile size.

### Slide R2: Segmentation result

- **Table:** manuscript Table 2 (Strokes per user). Verified against the stroke export:

  | User | Sessions | Strokes | Move | Drag |
  |---|---|---|---|---|
  | user7 | 121 | 14,790 | 14,027 | 763 |
  | user9 | 87 | 9,674 | 9,424 | 250 |
  | user12 | 191 | 17,023 | 16,341 | 682 |
  | user15 | 183 | 12,111 | 11,599 | 512 |
  | user16 | 163 | 14,606 | 14,092 | 514 |
  | user20 | 94 | 9,495 | 9,099 | 396 |
  | user21 | 99 | 7,845 | 7,776 | 69 |
  | user23 | 109 | 8,273 | 8,158 | 115 |
  | user29 | 104 | 8,399 | 8,230 | 169 |
  | user35 | 120 | 7,732 | 7,574 | 158 |
  | **Total** | **1,271** | **109,948** | **106,320** | **3,628** |

- **Optional small figure:** reuse `fig_m1_segmentation.png` panel (c) as a thumbnail.
- **On-slide text:**
  - **109,948 strokes** from 1,271 sessions; **every one** could be normalized
  - **96.7% move**, 3.3% drag
  - Median stroke: **17 points, 1.51 s** (from the export)
- **Say:** "Almost all strokes are plain moves, so the drag type contributes little to the matching."

### Slide R3: Experiment 1, accuracy per sensitivity

- **Figure:** `figures/exp1_graph.png` (manuscript Figure 1). Left = legitimate users, right = impostors, one line per split.
- **On-slide text:**
  - One session per user, sensitivity 0.01 → 1.00
  - Legitimate accuracy **rises** with sensitivity; impostor accuracy **falls**, because a looser tolerance lets more strokes of *any* user match
  - Best for impostors: **0.05**, the highest sensitivity where all 11 impostor sessions are still rejected
  - Best for legitimate users: **1.00**, where all 11 legitimate sessions are accepted (but so are all 11 impostors)
- **Say (to pre-empt a question):** "The curves are running totals, so the legitimate curve does not touch 1.0 at sensitivity 1.00 even though every legitimate session is accepted there."

### Slide R4: Experiment 1, best sensitivity = 0.05

- **Table:** manuscript Table 3 (verified, `exp1_points.csv`, sensitivity 0.05, 1 session):

  | Split (I x L) | TP | FP | FN | TN | Accuracy |
  |---|---|---|---|---|---|
  | 1x5 | 1 | 3 | 0 | 2 | 0.50 |
  | 5x1 | 5 | 0 | 0 | 1 | 1.00 |
  | 3x2 | 3 | 1 | 0 | 1 | 0.80 |
  | 2x3 | 2 | 2 | 0 | 1 | 0.60 |
  | **All** | **11** | **6** | **0** | **5** | **0.73** |

- **Figure (right side, smaller):** `figures/exp1_confusion.png` (manuscript Figure 2): TP 74, FP 71, FN 1,026, TN 1,029.
- **On-slide text:**
  - At 0.05: **all 11 impostor sessions rejected**; **6 of 11 legitimate sessions wrongly rejected**
  - Accuracy **0.73**, the highest of the 100 sensitivities (both groups have 11 sessions, so it is also the highest balanced accuracy)
  - Why 0.05 and not 1.00: at 1.00 every impostor gets in (accuracy 0.50); an impostor let in gains the account, while a blocked user can verify again
- **Say:** "The confusion matrix on the right adds all 100 sensitivities and all four splits (2,200 decisions). Most of those settings are loose, which is why it is dominated by accepted sessions. The row for the chosen setting is the table on the left."

### Slide R5: Experiment 2, accuracy per number of sessions

- **Figure:** `figures/exp2_graph.png` (manuscript Figure 3).
- **On-slide text:**
  - Sensitivity fixed at 0.05; sessions 5 → 40 in steps of 5
  - Legitimate accuracy stays **0.90–1.00**; impostor accuracy stays **below 0.15** and falls as sessions are added
  - Reason: a bigger library gives an impostor's strokes more strokes to match
  - Best: **5 sessions**, accuracy **0.53** (`exp2_overall.csv`: 0.5273; every larger library is 0.50–0.51)

### Slide R6: Experiment 2, best number of sessions = 5

- **Table:** manuscript Table 4 (verified, `exp2_points.csv`, sensitivity 0.05, 5 sessions):

  | Split (I x L) | TP | FP | FN | TN | Accuracy |
  |---|---|---|---|---|---|
  | 1x5 | 0 | 1 | 5 | 24 | 0.80 |
  | 5x1 | 3 | 0 | 22 | 5 | 0.27 |
  | 3x2 | 2 | 1 | 13 | 9 | 0.44 |
  | 2x3 | 1 | 1 | 9 | 14 | 0.60 |
  | **All** | **6** | **3** | **49** | **52** | **0.53** |

- **Figure (right side, smaller):** `figures/exp2_confusion.png` (manuscript Figure 4): TP 24, FP 6, FN 1,956, TN 1,974 (all 8 session counts, 3,960 decisions).
- **On-slide text:**
  - 52 of 55 legitimate sessions accepted; only **6 of 55 impostor sessions rejected**
  - With 5 sessions the profile accepts its owner but also most impostors
  - Output passed to feature extraction: **sensitivity 0.05, 5 sessions per profile**

### Slide R7: Discussion of this stage

- **On-slide text (keep to 3–4 bullets):**
  - DTW stroke matching alone **does not separate** users well: strict enough to block impostors (0.05) rejects 6 of 11 legitimate sessions; larger profiles let impostors through
  - The best values were chosen on the same sessions they score (likely optimistic), Experiment 1 rests on one session per user, and the results come from one seed (945)
  - This motivates the next stage: describing each user's movement **geometry** (hull members take over)
- **Say:** "This stage gives us the settings for building profiles. It also shows why matching stroke shapes one by one isn't enough, which is where the geometric features come in."

### Backup slide B1 (for panel questions): who was tested in each split

From `runs/19399f/<split>/results/accuracy.csv`. Only show it if asked.

| Split (I x L) | Legitimate users | Impostors |
|---|---|---|
| 1x5 | user29, user23, user20, user15, user9 | user16 |
| 5x1 | user29 | user15, user20, user23, user35, user9 |
| 3x2 | user29, user23 | user15, user20, user7 |
| 2x3 | user29, user23, user20 | user15, user9 |

Example (split 1x5, sensitivity 0.05, 1 session): user29 and user9 accepted, user23/user20/user15 rejected (FP 3, TN 2); impostor user16 matched 9 of 65 strokes (14% < 20%) and was rejected (TP 1).

---

## Panel questions to prepare for

| Likely question | Answer from the data |
|---|---|
| Why is the impostor the positive class? | Detecting an impostor is the event the system exists for, so a rejected impostor = TP. |
| Why 0.05 if legitimate users prefer 1.00? | At 1.00 all 11 impostors get in (accuracy 0.50); 0.05 has the highest accuracy (0.73) and blocks every impostor. |
| Why does the confusion matrix not match Table 3? | The figure adds all 100 sensitivities (2,200 decisions); Table 3 is the single setting 0.05. |
| Why only 0.53 in Experiment 2? | Bigger libraries make it easier for impostor strokes to find a match; accuracy at every library size is 0.50–0.53. |
| Why remove the 405 illegal sessions? | They are labelled as not belonging to the folder's user, so keeping them would mix impostor data into a user's own sessions. |
| Why normalize the strokes? | Users have different screens (1280×800 to 1920×1080) and sampling rates (~16 ms vs ~110 ms); moving to (0, 0), scaling and resampling compares shape, not position or speed of logging. |
