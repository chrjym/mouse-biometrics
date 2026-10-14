# `10_hull_anomaly.py`: anomaly test with the concave hull

[← index](README.md) · previous: [09](09_build_hulls.md) · next: [11](11_ocsvm_anomaly.md)

## What it does

Turns the hull of [09](09_build_hulls.md) into a **continuous-authentication test**. While someone uses the
computer, every stroke's displacement is checked against the account owner's hull. If too many recent strokes
fall outside, the session is flagged as "probably not the owner".

The script measures two errors:

- how often the owner's own sessions are wrongly flagged (**FRR**);
- how often other users' sessions get through (**FAR**).

Scripts [11](11_ocsvm_anomaly.md) and [12](12_dtw_anomaly.md) reuse this protocol, its window rule, and its
`summarize`, so all three methods are compared on equal terms.

Outputs: `runs/<run>/results/anomaly/{sessions,summary}.csv`, `figures/hull_anomaly.png`.

## Data: training sessions only

Only `training_files` are used here. Each training session certainly belongs to its folder's user, so FRR and
FAR are measured on clean labels. Balabit users have 5–7 training sessions each.

## Protocol

With $k$ = `anomaly_enroll_sessions` (4):

**Genuine sessions (FRR): leave-one-out.**

```
for each training session T of user u:
    enroll ← k random sessions of u, chosen from the others (Random(f"{seed}-{u}-{T}"))
    hull   ← concave hull of the end points of enroll
    score T against hull
```

**Impostor sessions (FAR).**

```
enroll ← k random sessions of u (Random(f"{seed}-{u}"))
hull   ← concave hull of their end points
for every other user v, for every training session of v: score it against hull
```

**Why leave-one-out?** With only 5–7 sessions per user, a fixed train/test split would leave one or two genuine
test sessions per user. Leave-one-out tests **every** session as genuine, and that session is never part of its
own profile, so there is no leakage.

**Why the same random draw strings in 10, 11, 12?** The three methods then enroll exactly the same sessions for
each test, so differences come from the method, not the data.

## Scoring one session (`score`)

1. For each stroke $i$ (in order), compute its displacement $e_i$ and test whether it is inside the hull
   (a **point-in-polygon** test, `shapely.contains_xy` [[1]](#ref-1)):
   $$o_i = \begin{cases} 1 & e_i \notin \text{hull} \\ 0 & \text{otherwise}\end{cases}$$
   `contains_xy` counts a point exactly on the outline as **not** inside, so such a stroke gets $o_i = 1$.
2. Slide a window of $W = \min(\texttt{anomaly\_window}, N)$ strokes over the session, one stroke at a time,
   and compute the share of outside strokes (a moving average, done with `np.convolve` [[2]](#ref-2)):
   $$w_j = \frac{1}{W} \sum_{i=j}^{j+W-1} o_i, \qquad j = 1, \dots, N - W + 1$$
3. A window is **flagged** when $w_j > \theta$, with $\theta$ = `anomaly_outside_share` (0.2).
4. The session is **flagged** when **any** window is flagged.
5. The session's **score** is its worst window, $s = \max_j w_j$ (`max_window_outside`).

**Why windows?** Continuous authentication must decide **during** the session, every few strokes, not after it
ends. A single stroke outside the hull is normal noise (about 4% of the owner's strokes fall outside). A window
of 30 strokes averages over that noise but still reacts within about 30 strokes. Earlier mouse-dynamics systems also decide on a group of actions
instead of a single one [[3]](#ref-3), [[4]](#ref-4). A session shorter than one
window is treated as one window.

**Why flag a session when any window is flagged?** In real use the system locks or re-authenticates the first
time a window looks wrong. The session's fate is therefore decided by its worst window.

## Error rates

The definitions follow standard biometric practice [[5]](#ref-5).

For a profile, with $G$ its genuine sessions and $I$ its impostor sessions:

$$\text{FRR} = \frac{|\{ s \in G : s \text{ flagged} \}|}{|G|}, \qquad
\text{FAR} = \frac{|\{ s \in I : s \text{ not flagged} \}|}{|I|}$$

### Equal Error Rate (`equal_error_rate`)

FRR and FAR depend on the cut $\theta$: a lower cut flags more sessions (more FRR, less FAR). The EER removes
that choice. With $t$ a cut on the worst-window score $s$:

$$\text{FRR}(t) = P(s_\text{genuine} \ge t), \qquad \text{FAR}(t) = P(s_\text{impostor} < t)$$

The code tries every observed score (plus $\infty$) as $t$, picks the cut where the two are closest, and returns
their mean there:

$$t^* = \arg\min_t |\text{FRR}(t) - \text{FAR}(t)|, \qquad \text{EER} = \tfrac{1}{2}\big(\text{FRR}(t^*) + \text{FAR}(t^*)\big)$$

**Why EER?** It is the standard single number for comparing biometric systems [[5]](#ref-5), and it does not depend on a
hand-picked cut. A method with a lower EER separates genuine from impostor sessions better at **some**
threshold. The fixed 20% rule can make one method look perfect on FAR and terrible on FRR (see script 12).

## Summary rows (`summarize`, `experiment_row`)

- **One row per user:** that user's profile against all 9 other users' sessions (user request, 2026-10-08).
- **Last row, the configured experiment:** one draw from `seed` (`01.draw_users`) fixes `n_legitimate` profiles
  and `n_impostor` impostors for the whole run (user decision, 2026-10-12). FRR comes from the legitimate users'
  own sessions, FAR from **those impostors only**, and the EER from the pooled scores.

Every profile has already been scored against every other user, so the draw only selects rows; nothing is
recomputed.

## Settings used

`anomaly_enroll_sessions` (4), `anomaly_window` (30), `anomaly_outside_share` (0.2), `concave_ratio`, `seed`,
`n_legitimate`, `n_impostor`, plus the segmentation settings.

## What we learned (4 sessions, window 30, 20%)

- FRR 24.6%, FAR 59.2%, **EER 43.8%** overall: only a little better than guessing.
- Best users: user9 (EER 15.8%) and user21 (20.9%).
- user15/16 have FAR of about 97–100%: their large-screen hulls contain other users' strokes.
- Own sessions have about 3.7% of strokes outside the hull, against 6.2% for other users. The two are too close
  to separate users reliably.

## References

<a id="ref-1"></a>[1] Shapely contributors, "shapely.contains_xy," Shapely 2 documentation. [Online]. Available: https://shapely.readthedocs.io/en/stable/reference/shapely.contains_xy.html

<a id="ref-2"></a>[2] NumPy developers, "numpy.convolve," NumPy documentation. [Online]. Available: https://numpy.org/doc/stable/reference/generated/numpy.convolve.html

<a id="ref-3"></a>[3] A. A. E. Ahmed and I. Traore, "A new biometric technology based on mouse dynamics," *IEEE Trans. Dependable Secure Comput.*, vol. 4, no. 3, pp. 165–179, Jul.–Sep. 2007, doi: [10.1109/TDSC.2007.70207](https://doi.org/10.1109/TDSC.2007.70207).

<a id="ref-4"></a>[4] M. Antal and E. Egyed-Zsigmond, "Intrusion detection using mouse dynamics," *IET Biometrics*, vol. 8, no. 5, pp. 285–294, 2019, doi: [10.1049/iet-bmt.2018.5126](https://doi.org/10.1049/iet-bmt.2018.5126).

<a id="ref-5"></a>[5] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).
