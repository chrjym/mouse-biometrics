# Experiment update: finding the sensitivity and the sessions

**Date:** 2026-10-19 · **Experiment:** EARL shape matching on Balabit (10 users, 1,676 sessions) · **Follows:** the
pipeline set on 2026-10-14 (user × user × sensitivity → user × session × sensitivity → heatmap)

## Summary

- We ran the pipeline on a **finer sensitivity grid** (0.01–0.50) for every split from 1 legitimate + 9 impostors to
  9 + 1, with 2–30 sessions per user: **6,750 runs** from one seeded draw.
- Users only differ between sensitivity **0.01 and 0.10**; above that, every user and every impostor gets through.
  The best setting is **sensitivity 0.03 with 8 sessions per user** in 7 of 9 splits, at a user accuracy of
  **0.52–0.71** (0.5 = chance).
- We found two reasons why impostors still get through: **simple strokes match everyone**, and **profiles with more
  strokes match everything**. A second scoring method that corrects for both looked better on the same draw
  (0.75–1.00).
- **Neither method holds on new draws.** Applied unchanged to three new seeds, both fall to about chance
  (0.44 and 0.42). Stroke shape alone does not identify users in Balabit.
- We propose adding **timing and speed** along each stroke, the "mannerisms" from the 2026-08-31 meeting, and
  would like your view before building it.

## 1. Setup

| Item | Value |
|---|---|
| Data | Balabit, all sessions, one folder per user (merged 2026-10-14) |
| Strokes | Mouse movement between pauses (> 0.5 s) or clicks, normalized for position and size, 64 points |
| Matching | Banded dynamic time warping (DTW) |
| Splits | 1–9, 2–8, …, 9–1 (legitimate–impostors), from one seeded draw (seed 927) |
| Sensitivity | 0.01 to 0.50 in steps of 0.01 (DTW distance per point; lower = stricter) |
| Sessions per user | 2, 4, …, 30 |
| Rules | A session goes through when ≥ 20% of its strokes match the profile; a user goes through when ≥ 50% of their sessions do |
| Tested sessions | Legitimate: the user's own sessions that were never in their profile. Impostor: their sessions against the legitimate profile that lets most of them in |

**User accuracy** = (legitimate users accepted / legitimate users + impostors rejected / impostors) / 2, the rule
agreed on 2026-10-14. **1 = perfect, 0.5 = chance** (the same as accepting or rejecting everyone).

## 2. Find the sensitivity and the sessions

![Best sensitivity and sessions per split](docs/figures/best_heatmaps.png)

*One panel per split. y = sensitivity, x = sessions per user, colour = user accuracy (white = chance, blue =
better, red = worse). Box = best cell. Sensitivities above 0.10 are not shown: every cell there is 0.5.*

| Split | Best sensitivity | Sessions | Legitimate accepted | Impostors through | User accuracy |
|---|---|---|---|---|---|
| 1–9 | 0.03 | 8 | 1/1 | 6/9 | 0.67 |
| 2–8 | 0.03 | 8 | 2/2 | 5/8 | 0.69 |
| 3–7 | 0.03 | 8 | 3/3 | 4/7 | 0.71 |
| 4–6 | 0.03 | 8 | 4/4 | 4/6 | 0.67 |
| 5–5 | 0.03 | 8 | 5/5 | 3/5 | 0.70 |
| 6–4 | 0.03 | 8 | 5/6 | 2/4 | 0.67 |
| 7–3 | 0.03 | 8 | 5/7 | 2/3 | 0.52 |
| 8–2 | 0.01 | 2 | 0/8 | 0/2 | 0.50 |
| 9–1 | 0.01 | 2 | 0/9 | 0/1 | 0.50 |

- The 0.2–1.0 grid from 2026-10-14 saturates, as we saw then; the useful range is 0.02–0.04.
- Even at the best setting, **at least half of the impostors get through** in every split up to 7–3. In 8–2 and
  9–1 no setting beats chance: the "best" is the one where nobody goes through.

## 3. Why legitimate users and impostors cannot be separated

![Sessions through per user, 3 legitimate vs 7 impostors, sensitivity 0.03](docs/figures/accuracy_3_7_sensitivity_0.03.png)

*Left: own sessions that go through, per legitimate user. Right: impostor sessions that go through, per impostor.
One line per sessions per user (dark = 2, light = 30).*

The legitimate and impostor lines rise **together and to the same height**: at 30 sessions, user7 passes 26 of 30
of their own sessions, while user29 passes 30 of 30 as an impostor. Any sensitivity that lets the user in lets the
impostors in too. Two causes:

1. **Simple strokes match everyone.** Most matched pairs are near-straight lines or plain curves. After
   normalization, these look the same for every user.
2. **Bigger profiles match everything.** With 2 sessions, user16's and user23's profiles held about 1,000 strokes,
   user9's only 39. Impostors claiming the large profiles scored as high as the genuine users.

## 4. A second method: compare against other people

To correct both causes, we scored each stroke by **whether it lies closer to the claimed user's profile than to
other people's** (cohort scoring, as used in speaker verification), with **every profile cut to the same number of
strokes**.

![One genuine session, stroke by stroke](docs/figures/claim_user16_genuine.png)

*One genuine session of user16. Each row is one stroke (black); column 1 = the nearest stroke in user16's profile
(blue); the other columns = the nearest stroke in each other person's profile: red = closer than user16's (counts
against), grey = farther (counts for). Bottom: the ranks of all strokes; the session score is their mean (0.5 =
no evidence).*

Some strokes do point clearly to the right user (top row: every other person is farther), but just as many point
to someone else. Genuine sessions average **0.514** and impostor sessions **0.499**, so the two overlap almost
completely.

![Cohort scoring: EER and best user accuracy per split](docs/figures/cohort.png)

*Left: equal error rate per split (lower = better, 0.5 = chance); solid = cohort, dashed = plain distance. Right:
best user accuracy per split for the matching of section 2 (grey) and the two new scores (blue).*

On the same draw, the cohort score has a lower error rate than plain distance in most splits (EER 0.30–0.39 at the
session count it picks) and a higher best user accuracy than matching in every split (0.75–1.00).

## 5. Do the chosen settings hold on new draws?

Sections 2 and 4 choose the best setting on the same draw they score, which makes their numbers optimistic. We
applied each method's chosen setting **unchanged** to three new seeds: new users in each role, new sessions.

![Chosen settings on new seeds](docs/figures/seed_check.png)

*Light bar = user accuracy on the draw where the setting was chosen (seed 927); dark bar = mean over the new seeds
(928–930); dots = each new seed; dotted line = chance.*

| Method | Chosen draw (seed 927) | New draws (mean of 3) |
|---|---|---|
| Matching with the best sensitivity and sessions (section 2) | 0.63 | 0.44 |
| Plain distance | 0.70 | 0.50 |
| Cohort score (section 4) | 0.82 | 0.42 |

*User accuracy averaged over the 9 splits.*

**All three fall to about chance.** The cohort score falls the most, because its threshold was tuned to one draw.
Only the 1–9 split stays above 0.5 on average, and not on every seed.

## 6. Conclusion

On Balabit, **the shape of short mouse strokes, compared with DTW, does not identify a user** once the setting is
tested on users and sessions it was not chosen on. This holds for every sensitivity, session count and split we
tried, and for both scoring methods. What we learned along the way is still useful for the thesis: the useful
sensitivity range, the bias from profile size, and the evidence that common strokes carry no identity.

## 7. Proposed next step and questions

**Proposal:** keep the strokes and DTW, but compare **how** each stroke is drawn, not only its shape: speed along
the stroke, where the user slows down, pauses and small corrections. These are the user mannerisms from the
2026-08-31 meeting. Balabit users log at different rates (every 16 ms or every 110 ms), so the strokes would first
be resampled by time; otherwise we would measure the logging rate, not the person.

**Questions for you:**

1. Do you agree that the shape-only result is final, and that we report it as a negative result?
2. Should the next step be timing and speed features, or do you prefer another direction?
3. Should all results be checked on new seeds from now on, as in section 5?
4. The whiteboard on 2026-10-14 showed seed = 41. Should we rerun with seed 41, or keep a set of seeds as in
   section 5?
