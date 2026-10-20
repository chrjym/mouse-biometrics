# `19_cohort_score.py`: cohort scoring, a session must look more like its user than like other people

[← index](README.md) · previous: [18](18_pick_best.md) · next: [20](20_seed_check.md)

## What it does

Scripts 16 and 18 accept a stroke when it lies within `sensitivity` of **any** stroke in the claimed user's library.
That rule has two weak points: common strokes (near-straight lines) match everyone, and a library with more strokes
is closer to everything. This script replaces the yes/no match with two continuous scores per session and compares
them with 18's best result on the same hash folder (same seed, users and session orders):

- **raw**: minus the mean nearest DTW cost per point from the session's strokes to the claimed user's library.
- **cohort**: for each stroke, the share of *other people* whose library is farther from it than the claimed user's
  library; the session score is the mean over its strokes. 0.5 = the strokes look no more like the claimed user than
  like anyone else.

Outputs, in `runs/<hash>/cohort/`:

- `sessions.csv`: one row per claim (session, author, claimed user, genuine or not) with both scores.
- `cells.csv`: per (split, sessions per user, method) the EER and, at the threshold with the best user accuracy,
  users through on each side, user accuracy and session accuracy.
- `best.csv`: per split, the best session count for each method next to 18's best (`match_*` columns).
- `cohort.png`: left, EER per sessions per user, one line per split (solid = cohort, dashed = raw); right, best user
  accuracy per split for 18's matching, raw and cohort.

```bash
.venv/bin/python experiment_earl/src/19_cohort_score.py 251ea4                     # sessions 2–10
.venv/bin/python experiment_earl/src/19_cohort_score.py 251ea4 --max-sessions 30   # the whole batch range, much slower
```

The settings are flags, not `config.yaml` keys, because a new key would change every run hash. Nearest costs are
cached in `experiment_earl/cache/nearest.pkl` (git-ignored); a rerun with the same settings only rescores.

## Algorithm

```
users, session orders ← 14.draw_users(seed) with 9 legitimate users   # every split takes its legitimate users
                                                                        # from the front of this order
for k in the hash folder's session counts (≤ --max-sessions):
    budget ← k × strokes_per_session
    per user u: half ← (pool size − max k) / 2
        profile(u)    ← u's sessions from the front half, in order, until they hold budget strokes
        background(u) ← the same from the back half
        both cut to exactly budget evenly spaced strokes
    claims: u's last k sessions as u (genuine); v's first k sessions as every other user u (impostor)
    per claim (author v, claimed u), others ← every user except u and v:
        d_u(s) ← nearest banded DTW cost of stroke s to profile(u)          (same kind only)
        d_w(s) ← nearest cost to background(w) for each w in others
        raw    ← − mean_s d_u(s)
        cohort ← mean_s ( share of w with d_w(s) > d_u(s), ties count ½ )
per split (L legitimate, I impostors), k, method:
    EER over the split's claims (legitimate users' genuine claims; impostors' claims of the legitimate users)
    threshold t with the best user accuracy (18's rule; ties: session accuracy)
per split and method: the k with the best user accuracy (ties: session accuracy, then fewer sessions)
```

## Formulas

Nearest cost per point, with the banded DTW of [04](04_match_shapes.md) and $n$ = `resample_n`:

$$d_u(s) = \min\left(\texttt{cap},\ \min_{p \in \text{profile}(u)} \frac{\text{DTW}(s, p)}{n}\right)$$

$$\text{cohort}(S, u) = \frac{1}{|S|} \sum_{s \in S} \frac{1}{|W|} \sum_{w \in W}
\left( [d_w(s) > d_u(s)] + \tfrac{1}{2} [d_w(s) = d_u(s)] \right), \qquad W = \text{users} \setminus \{u, v\}$$

A session is accepted when its score is at least $t$. EER is the rate where the share of genuine sessions rejected
equals the share of impostor sessions accepted.

## Why these choices

- **Compare against other people (cohort or background normalization).** Speaker verification uses the same idea:
  a claim is judged by how much better it fits the claimed model than other people's models. A near-straight
  stroke is close to every library, so it scores about ½ and adds no evidence; only strokes that fit the claimed
  user better than others move the score.
- **Every library holds the same number of strokes.** With 2 sessions per library, user16's and user23's profiles
  had ~1,000 strokes and user9's 39; impostors claiming user16 or user23 scored 0.92–0.94 (as high as genuine), and
  the score fell in line with profile size. Equal stroke budgets remove that: a profile is "k × 40 strokes", taken
  from as many sessions as needed (40 ≈ the median strokes per session). Cutting every library to the smallest one
  instead left 13 strokes at 2 sessions.
- **The author is left out of the others, and backgrounds come from other sessions.** The attacker is unseen, as in
  a real deployment, and no tested session is ever part of a library: profiles and backgrounds come from the two
  halves of the pool before the last max-k sessions, which are the genuine tests. Impostor tests are the author's
  first k sessions, but the author's own libraries are never used in their claims.
- **EER and the best threshold.** EER needs no threshold, so it is the fairest comparison between raw and cohort.
  The user accuracy uses the threshold that maximizes it on the same claims, like 18 picks its best sensitivity on
  the same runs, so both are optimistic; [20](20_seed_check.md) checks the chosen settings on new seeds.
- **`--cap` 0.5.** Above a cost of about 0.1 per point the batch matched everything, so costs above 0.5 are treated as
  equally far; the cap also lets the DTW stop early.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
