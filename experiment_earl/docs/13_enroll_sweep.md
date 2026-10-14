# `13_enroll_sweep.py`: how many registered sessions does each method need?

[← index](README.md) · previous: [12](12_dtw_anomaly.md)

## What it does

Reruns the three anomaly tests, hull ([10](10_hull_anomaly.md)), One-Class SVM ([11](11_ocsvm_anomaly.md)) and
DTW ([12](12_dtw_anomaly.md)), with $k = 1, 2, \dots,$ `anomaly_enroll_sessions` registered (enrolled) sessions.
It reports FRR, FAR and EER at each step. The question: **does a profile built from more sessions recognise its
owner better?**

Outputs: `runs/<run>/results/enroll_sweep/{sessions,summary}.csv`, `results/enroll_sweep/progress.pkl`,
`figures/enroll_sweep_lines.png`, `figures/enroll_sweep_heatmap.png`.

## Algorithm

### A method table (`METHODS`)

Each method is described by the same four pieces, taken from its own script, so the protocol is written once:

| | `prepare` (per session) | `build` (profile from $k$ sessions) | `score` (session vs profile) | worst-window column, direction |
|---|---|---|---|---|
| hull | `10.end_points` → displacements | `10.build_hull` → concave hull | `10.score` | `max_window_outside`, high = anomalous |
| ocsvm | `11.session_features` → 6 features | `11.fit` → scaler + SVM | `11.score` | `worst_window_score`, low = anomalous |
| dtw | `12.session_shapes` → normalized shapes | `12.build_library` → shape library | `12.score(12.anomalous(…))` | `max_window_outside`, high = anomalous |

### The shared protocol (`evaluate`)

```
for k in 1 … k_max:
  for each user u:
    genuine:  for each training session T of u:
                  order  ← Random(f"{seed}-{u}-{T}").sample(other sessions of u, k_max)
                  profile ← build(order[0:k]);  score T
    impostor: order   ← Random(f"{seed}-{u}").sample(sessions of u, k_max)
              profile ← build(order[0:k]);  score every training session of every other user
```

### Why "first k of a draw of k_max" reproduces scripts 10–12

Scripts 10–12 call `sample(sessions, k)` directly. Python's `random.sample` [[1]](#ref-1), on lists this small, picks elements
one at a time with the same random numbers whatever $k$ is, so `sample(x, k)` equals the first $k$ elements of
`sample(x, k_max)`. Therefore:

- step $k$ registers **exactly** the sessions scripts 10–12 would register with $k$ sessions (step 4 reproduces
  their EERs);
- the steps are **nested**: step $k+1$ adds one session to step $k$. A change between steps is due to that
  session, not to a new random draw.

### Summary

Per method and $k$, `10.summarize` gives one row per user and the configured-experiment row (one fixed draw of
legitimate users and impostors). The EER uses the hull's function for "high is anomalous" methods and the SVM's
for "low is anomalous". The formulas are in [10](10_hull_anomaly.md#equal-error-rate-equal_error_rate).

### Resume

Each finished (method, $k$, user) cell is saved to `progress.pkl`. `--method` runs only some methods. Hull and SVM
take about 30 s; DTW takes about 25 min.

## Figures

- `enroll_sweep_lines.png`: FRR, FAR and EER (configured-experiment row) against $k$, one line per method.
- `enroll_sweep_heatmap.png`: EER as a method × $k$ grid, coloured 0–1 in 0.1 steps (0 = perfect, 0.5 = chance).

## Why this experiment

Error rates are defined as in 10 [[2]](#ref-2). A real system has to choose how long to watch a new user before trusting their profile. If the EER fell clearly
with $k$, that would show how many sessions are enough. If it does not fall, then more enrollment data does not
fix the method's weakness.

## What we learned (earlier per-draw protocol, 3 legitimate + 2 impostors, 20 draws, k = 1 → 4)

The EER barely moves for any method:

| method | k = 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| hull | 44.6% | 49.6% | 46.3% | 44.5% |
| SVM | 24.8% | 26.4% | 25.1% | 27.7% |
| DTW | 45.7% | 41.8% | 44.3% | 46.5% |

Each value varies by ± 13–20% between draws. More sessions **trade FRR for FAR** without separating users better:
the profile grows, so fewer own sessions are rejected but more impostors fit inside.

- hull: FRR 89.8 → 27.5%, FAR 14.5 → 56.5%
- SVM: FRR 33.4 → 8.2%, FAR 24.2 → 34.2%

## References

<a id="ref-1"></a>[1] Python Software Foundation, "random — Generate pseudo-random numbers," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/random.html

<a id="ref-2"></a>[2] A. K. Jain, A. Ross, and S. Prabhakar, "An introduction to biometric recognition," *IEEE Trans. Circuits Syst. Video Technol.*, vol. 14, no. 1, pp. 4–20, Jan. 2004, doi: [10.1109/TCSVT.2003.818349](https://doi.org/10.1109/TCSVT.2003.818349).
