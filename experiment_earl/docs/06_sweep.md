# `06_sweep.py`: full sweep over sessions, legitimate users and impostors

[← index](README.md) · previous: [05](05_threshold.md)

## What it does

Runs the shape-matching experiment of 01–05 for **every** combination of

- sessions per user $k = 1 \dots$ `sweep_sessions_max`,
- legitimate users $n_L = 1 \dots 9$,
- impostor users $n_I = 1 \dots 10 - n_L$,

over `n_trials` random draws (seeds `seed`, `seed + 1`, …). It reports how the threshold changes along each
axis: where the curve **saturates** (stops changing) and where its **biggest jump** is.

Outputs (in the run folder): `results/sweep/{pairs,summary,saturation}.csv`, `results/sweep/settings.json`,
`figures/sweep_heatmaps.png`, `figures/sweep_lines.png`.

## Algorithm

### 1. One draw per seed (`draw`)

The shuffle is Python's Fisher–Yates shuffle [[1]](#ref-1), [[2]](#ref-2).

```
users ← the 10 users, shuffled with Random(seed)
legitimate users of a cell with n_L  ← users[0 : n_L]            (from the front)
impostors of a cell with n_I         ← reversed(users)[0 : n_I]   (from the back)
sessions of user u with k            ← session_pool(u, seed)[0 : k]
```

Taking legitimate users from the front and impostors from the back means:

- the two sets never overlap while $n_L + n_I \le 10$;
- every set is **nested**: the cell with 3 legitimate users contains the 2 users of the cell with 2.

Neighbouring cells therefore differ by exactly one user or one session, so a change in the threshold can be
traced to that one difference instead of to a new random draw.

### 2. Score every user pair once (`pair_scores`)

The outcome of a cell depends only on scores between single pairs of users. So for every $k$ and every ordered
pair (impostor $v$, legitimate $u$), $v \ne u$, the script computes, once:

$$\text{share}_k(v, u) = \frac{1}{k}\sum_{s \in S_v^{(k)}} \mathbb{1}\big[r_{s,u} \ge \sigma\big], \qquad
\text{mean\_ratio}_k(v,u) = \frac{1}{k}\sum_{s \in S_v^{(k)}} r_{s,u}$$

with $r_{s,u}$ the session match ratio of script 04 against $u$'s first $k$ sessions. That is
$10 \times 9 = 90$ pairs per $k$ per seed, stored in `pairs.csv`.

### 3. Build every cell from the pairs (`cell_results`)

$$\text{matched}(k, n_L, n_I) = \sum_{v \in I}\ \mathbb{1}\Big[\max_{u \in L} \text{share}_k(v, u) \ge \rho\Big],
\qquad \text{threshold} = \frac{\text{matched}}{n_I}$$

This is exactly the rule of scripts 04–05 ("an impostor is matched if any single profile accepts them"). With 10
users there are $\sum_{n_L=1}^{9} (10 - n_L) = 45$ cells per $k$.

**Why score pairs instead of cells?** Running 01–05 per cell would compare the same pair of users again in
every cell that contains both. Scoring the 90 pairs once and combining them with a max and a count gives the
same answer for all 45 cells at a fraction of the cost.

### 4. Average over draws

For each cell: the mean and standard deviation of `matched` and `threshold` over the seeds (`summary.csv`).

### 5. Saturation and biggest jump (`saturation`)

For a curve of means $m_1, m_2, \dots, m_K$ along one axis, with changes $\Delta_i = m_i - m_{i-1}$ and
$\delta$ = `sweep_delta`:

$$\text{flat\_from} = \min\big\{\, s : |\Delta_i| < \delta \text{ for every } i > s \,\big\}$$

$$\text{biggest\_jump\_at} = \arg\max_i |\Delta_i|, \qquad \text{biggest\_jump} = \max_i |\Delta_i|$$

The code walks backwards from the last step and stops at the first change that is $\ge \delta$.

This rule is our own; it is not taken from a published method. **Why this rule?** "Saturation" answers a practical question: *after how many sessions (or users) does adding
more stop changing the result?* That is the smallest enrollment worth asking for. Walking backwards makes sure
the curve stays flat to the end, not just for one step. The biggest jump shows where adding data matters most.
It is done for each axis, with the other two fixed (`saturation.csv`).

### Resume

Seeds already in `pairs.csv` are skipped. A rerun with the same settings only redraws the figures. The first run
takes about 30 minutes, because it fills the shared DTW cache.

## Figures

- `sweep_heatmaps.png`: one heatmap per $k$, with legitimate users on x, impostors on y, and the mean threshold
  as colour in 0.1 steps.
- `sweep_lines.png`: the threshold against each axis, one line per value of a second axis, averaged over the
  third.

## Settings used

`sweep_sessions_max`, `sweep_delta`, `n_trials`, `seed`, plus all matching settings of 04.

## What we learned (tolerance 0.02, 20 draws)

- **Sessions per user** drive the threshold: going from 1 to 2 sessions adds about 0.2, and the curve is flat
  from about 4 sessions.
- **Legitimate users** give a slow rise: 0.16 → 0.27 from 1 to 9 users (more profiles = more chances that one
  accepts the impostor).
- **Impostor count** barely matters, because the threshold is already a share.

## References

<a id="ref-1"></a>[1] R. Durstenfeld, "Algorithm 235: Random permutation," *Commun. ACM*, vol. 7, no. 7, p. 420, Jul. 1964, doi: [10.1145/364520.364540](https://doi.org/10.1145/364520.364540).

<a id="ref-2"></a>[2] Python Software Foundation, "random — Generate pseudo-random numbers," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/random.html
