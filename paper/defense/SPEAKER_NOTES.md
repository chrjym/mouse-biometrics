# Speaker Notes: Raw Data to Confusion Matrix

Every "Say:" line from `DEFENSE_SLIDES_GUIDE.md`, in slide order. Slides without one are listed so the order stays complete. For the slide content, figures and tables, see the guide.

---

## Category 1: Methodology

### Slide M1: Process overview

"Before we describe a user's shape, we have to decide how strict the matching is and how many sessions make a profile. This part of the method answers those two questions with two experiments scored by a confusion matrix."

### Slide M2: Data acquisition and organization

"Every session is a stream of cursor records. We keep each session under its owner, and drop the 405 the dataset marks as illegal, so every remaining session belongs to the user it is filed under."

### Slide M3: Preprocessing and segmentation

"Normalizing removes where on the screen and how big the movement was, so only the shape remains. This matters because Balabit users have different screens and sampling rates."

### Slide M4: Matching strokes with DTW

"Sensitivity is the tolerance. At 0.01 two strokes must be almost identical; at 1.00 almost anything matches. Experiment 1 finds the right value."

*With the diagram (`matching_dtw_diagram.png`), which has no source line:*
"The strokes are real user29 strokes. The bars are from run 19399f, split 1x5, sensitivity 0.05, one session: user29's own session matched 19 of 66 strokes against its own library; impostor user16 matched 9 of 65 against user9's library, its best."

### Slide M5: Profiles, splits and the confusion matrix

"We treat catching an impostor as the positive event, because that is what an authentication system exists to do."

### Slide M6: The two experiments

"Experiment 1 fixes strictness, Experiment 2 uses it to decide how many sessions a profile needs. Those two values are passed on to the feature extraction."

*With the diagram (`two_experiments_diagram.png`), which leaves out the running-total line:*
"The graphs add each setting's counts to the ones before it, and each confusion matrix is the total at the last setting."

---

## Category 2: Results and Discussion

### Slide R1: Data acquisition result

*(No "Say:" in the guide.)*

### Slide R2: Segmentation result

"Almost all strokes are plain moves, so the drag type contributes little to the matching."

### Slide R3: Experiment 1, accuracy per sensitivity

*(To pre-empt a question)* "The curves are running totals, so the legitimate curve does not touch 1.0 at sensitivity 1.00 even though every legitimate session is accepted there."

### Slide R4: Experiment 1, best sensitivity = 0.05

"The confusion matrix on the right adds all 100 sensitivities and all four splits (2,200 decisions). Most of those settings are loose, which is why it is dominated by accepted sessions. The row for the chosen setting is the table on the left."

### Slide R5: Experiment 2, accuracy per number of sessions

*(No "Say:" in the guide.)*

### Slide R6: Experiment 2, best number of sessions = 5

*(No "Say:" in the guide.)*

### Slide R7: Discussion of this stage

"This stage gives us the settings for building profiles. It also shows why matching stroke shapes one by one isn't enough, which is where the geometric features come in."

### Backup slide B1: Who was tested in each split

*(No "Say:" in the guide. Show only if asked.)*
