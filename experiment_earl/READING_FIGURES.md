# How to read the figures

Every figure the EARL experiment makes, what one mark in it means, what a good and a bad result look like, and
what we saw so far. How to *make* each figure is in [README.md](README.md); how each script computes it is in
[docs/](docs/README.md).

All examples come from `runs/251ea4/` (seed 927, the batch of 9 splits × 50 sensitivities × 15 session counts),
unless a section says otherwise. `runs/` is git-ignored, so copies of the example figures live in
[docs/figures/](docs/figures/); your own figures are in the run folders named under each heading.

## Contents

1. [Words used in every figure](#1-words-used-in-every-figure)
2. [Which figures to read, in what order](#2-which-figures-to-read-in-what-order)
3. [Shapes of single strokes](#3-shapes-of-single-strokes-c) (C)
4. [Notebook: one run, sessions 1 → N](#4-notebook-one-run-sessions-1--n-a) (A)
5. [Matched shapes and the genuine check](#5-matched-shapes-and-the-genuine-check-d-e) (D, E)
6. [Sessions through across the runs of a batch](#6-sessions-through-across-the-runs-of-a-batch-f) (F)
7. [The best sensitivity and sessions](#7-the-best-sensitivity-and-sessions-g) (G)
8. [Mistakes to avoid when reading them](#8-mistakes-to-avoid-when-reading-them)

The letters match the sections of [README.md](README.md). Sections for the cohort scoring (H, J) and the new-seed check (I) were removed on 2026-10-26 together with their scripts; their results are still in the dated [INITIAL_RESULT_2026-10-19.md](INITIAL_RESULT_2026-10-19.md).

---

## 1. Words used in every figure

| Word | Meaning |
|---|---|
| **Session** | One Balabit recording file. It belongs to the user whose folder it is in. |
| **Stroke** (chunk, shape) | A piece of mouse movement between two pauses or clicks. Strokes are moved to start at (0, 0), scaled to the same size and redrawn with 64 points before they are compared, so only the *shape* is left. |
| **Profile / library** | The strokes of a legitimate user's first *k* sessions. New sessions are compared against it. |
| **Legitimate user** | The user a profile belongs to. Their own unused sessions *should* match. |
| **Impostor** | Any other user. Their sessions *should not* match. |
| **Split** `L–I` | `L` legitimate users and `I` impostors from one draw, e.g. `3–7`. Always 10 users in total. |
| **Sessions per user** (*k*) | How many sessions build each profile and how many are tested per user. |
| **Sensitivity** | The DTW tolerance: two strokes match when their distance per point is at most this. **Lower = stricter.** Around 0.15 almost everything matches. (In the notebook heatmap, *sensitivity* is also the share of impostors matched; see section 4.) |
| **A session goes through** | At least `match_shape_ratio` (20%) of its strokes match the profile. |
| **A user goes through** | At least `match_session_ratio` (50%) of their tested sessions go through. For a legitimate user that is good (accepted); for an impostor it is bad (got in). |
| **User accuracy** | (share of legitimate users accepted + share of impostors kept out) / 2. **1 = perfect, 0.5 = chance** (the same as accepting everyone or rejecting everyone). |
| **Session accuracy** | The same, counted over sessions instead of users. Stricter than user accuracy. |
| **Seed** | The random number that picks the users, the split and every session order. Same seed = same draw. |

**Chance is 0.5 everywhere.** Any accuracy near 0.5 means the method cannot tell users apart in that setting,
however the bars or colours look.

## 2. Which figures to read, in what order

For the thesis question ("do short mouse strokes identify a user?"):

1. **Section 3 (shape PNGs)** and **section 5 (matched shapes)**: what strokes look like, and why they match across
   users.
2. **Section 6 (sessions through)**: the raw counts per user for every run.
3. **Section 7 (best heatmaps)**: which sensitivity and session count work best per split. These are the best of
   many settings on the same data, so do not read them as a result on their own (section 8).

---

## 3. Shapes of single strokes (C)

**File:** `runs/<hash>/<run>/shapes/<legitimate|impostor>/<user>/<session>/chunk_NNNN_<move|drag>.png` and
`overview.png` (the first 100 strokes of a session in a grid).

- **One image = one stroke**, in real screen coordinates (y grows downward, as on the screen).
- Green dot = start, red dot = end. Blue line = mouse move, orange line = drag (a button held).
- The title gives the stroke number, its length in pixels and its duration.

**What to look for:** how many strokes are near-straight lines. Those are the strokes that later match everyone.

## 4. Notebook: one run, sessions 1 → N (A)

Folder: `runs/<hash>/<run>/figures/`. One draw from the seed fixes the users and sessions; the profile grows one
session at a time (step *k* + 1 keeps the sessions of step *k*).

### `session_progression.png`: impostors matched per session step

- **x** = sessions per user (1, 2, … `sessions_per_user`). **y** = how many impostor users matched at least one
  legitimate profile.
- **Lower is better.** A good method keeps the bars low while the profile grows.
- Bars that rise with *k* mean a bigger profile lets more impostors in.

### `session_progression_users.png`: the same count, one panel per legitimate user

- One panel per legitimate user; each bar = impostors (of all `I`) that matched **that** user's profile at that
  session step. The tallest bar of each panel is red.
- Compare panels: a user whose bars are always high (here user16, 3–5 of 7) has a "permissive" profile that
  impostors match easily; a user near 0 (user15) is hard to imitate.

![Impostors matched per legitimate user](docs/figures/session_progression_users.png)

### `session_progression_heatmap.png`: sessions × legitimate users

- **y** = sessions per user, **x** = number of legitimate users (the first 1, 2, … of the draw).
- **Colour = sensitivity in the notebook's sense: impostors matched / impostors** (0 = no impostor got in = best,
  1 = every impostor got in). Each cell also prints the count, e.g. `0.57 (4 of 7)`.
- Columns that are all the same (as in the example) mean the first legitimate user already matches every impostor
  that the others would; adding users adds nothing.

## 5. Matched shapes and the genuine check (D, E)

Scripts 08 and 09 no longer draw figures (removed 2026-10-26); they write tables only.

- **`results/matches.csv`** (script 08): one row per matched stroke: the legitimate user's profile, the impostor and
  session, the stroke's chunk number and the matched stroke's chunk number, with the DTW cost per point. Open the
  matched stroke pairs with a plotting tool of your choice if you need to see them. **What we saw:** most matched
  pairs are near-straight lines, which look the same for everyone after normalization.
- **`results/genuine_check_summary.csv`** (script 09): per legitimate user, session step and kind (genuine =
  the user's own unused sessions, impostor = the impostors' sessions): mean share of strokes matched and the
  sessions passed / tested. **Good result:** the genuine share clearly above the impostor share and above
  `match_shape_ratio`.

## 6. Sessions through across the runs of a batch (F)

**File:** `runs/<hash>/accuracy.csv` (script 10). The PNG figures were removed on 2026-10-26; the table has the same
counts.

- **Legitimate users:** **how many of their own last *k* sessions** (never used in a profile) go through their own
  profile. **Higher is better.**
- **Impostor users:** **how many of their first *k* sessions** go through the legitimate profile that lets most of
  them in. **Lower is better.**
- **A user is through** when at least 50% of their tested sessions go through.

**What we saw (sensitivity 0.03, 3 legitimate vs 7 impostors):** the legitimate counts and the impostor counts rise
together with the number of sessions. At 30 sessions, user7 passes 26 of 30 own sessions, but user29 passes 30 of 30
as an impostor. The method cannot separate them: whatever lets the legitimate user in also lets the impostors in.
Only user21 is consistently harder to pass as.

**Also in the hash folder:** `summary/README.md` (written by the batch, script 11): a table of every run (legitimate
passed and accepted, impostors passed and through) with links to the run folders.

## 7. The best sensitivity and sessions (G)

**File:** `runs/<hash>/best/best_heatmaps.png` (script 12).

![Best heatmaps](docs/figures/best_heatmaps.png)

- **One panel per split.** **y** = sensitivity, **x** = sessions per user. Sensitivities above 0.10 are left out
  (the title says so), because every cell there is exactly 0.5: everyone goes through.
- **Colour = user accuracy around chance:** white = 0.5 (chance), **blue = better than chance**, **red = worse than
  chance** (more impostors than legitimate users get through).
- **Black box** = the best cell of that split; the panel title gives its value, e.g. `best 0.71 (sessions 0.61) at
  0.03 / 8 sessions`. "= chance" means no cell beat 0.5.

**How to read the example:** almost all the colour is in one thin band at sensitivity 0.02–0.04; the rest is
white. The best cell is 0.03 / 8 sessions in 7 of 9 splits, at 0.52–0.71. In 8–2 and 9–1 nothing beats chance, so
the "best" box sits on 0.01 / 2 sessions, where nobody goes through.

**Also in `best/`:** `best.csv` (the boxed cells) and `scores.csv` (every cell).

## 8. Mistakes to avoid when reading them

- **Treating a "best" value as a result.** Section 7 shows the best of thousands of settings, chosen on the same
  data. Nothing in this folder tests a setting on data it was not chosen on (the new-seed check was removed on
  2026-10-26).
- **Comparing counts across runs.** In section 6 the numbers are session *counts* up to *k*; compare a row with its
  own maximum, not with another run.
- **Reading "sensitivity" the same way everywhere.** In sections 6 and 7 it is the DTW tolerance (lower = stricter).
  In the notebook heatmaps (section 4) the colour called sensitivity is the **share of impostors matched**
  (lower = better).
- **Reading colour without the midpoint.** In `best_heatmaps.png` white is chance (0.5), not zero; red cells are
  *worse* than chance.
- **Trusting one-user splits.** With 1 legitimate user, user accuracy can only be 0, 0.5 or 1 on the legitimate
  side, so a single lucky session moves it a lot.
- **Forgetting the screen-size and sampling-rate differences.** Users log every 16 ms or every 110 ms and use
  different screens; shapes are normalized for size, but timing-based figures would measure the logging rate, not
  the person.
