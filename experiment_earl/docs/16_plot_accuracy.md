# `16_plot_accuracy.py`: how many strokes go through, per user, across runs

[← index](README.md) · previous: [15](15_genuine_check.md)

## What it does

Compares every run inside one hash folder, `runs/<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>/`.
Runs in one hash folder share every other setting (seed, chunking, matching), so they differ only in those four values.
For each run it scores every drawn user. Per `sensitivity` it draws one figure with two line graphs side by side:

- **Legitimate users:** x = each legitimate user, y = share of their own strokes that match their own profile.
- **Impostor users:** x = each impostor user, y = share of their strokes that match the legitimate profile that matches them most.

One line per run of that sensitivity, i.e. per `sessions_per_user` (lighter = more sessions).

Outputs (in the hash folder, not in a run): `runs/<hash>/accuracy.csv`, `runs/<hash>/accuracy_sensitivity_<value>.png` (one per sensitivity).

## Algorithm

```
for each run folder under runs/<hash>/ (its own config.yaml snapshot):
    legitimate, impostors, order ← 14.draw_users(config, seed)       # the notebook's draw
    library[u] ← u's first sessions_per_user sessions
    legitimate u: test u's last 2 sessions of the pool against library[u]
    impostor v:   test v's first sessions_per_user sessions against every library[u]; keep the best profile
accuracy = matched strokes / strokes                                  # 04.matched_chunks, shared DTW cache
```

## Formulas

$$\text{accuracy}(v, P) = \frac{\sum_{s \in S_v} \text{matched\_chunks}(s, P)}{\sum_{s \in S_v} \text{strokes}(s)}$$

For an impostor $v$, the reported value is $\max_P \text{accuracy}(v, P)$ over the legitimate profiles $P$.
A stroke matches when its banded DTW distance per point to some profile stroke is at most `sensitivity` (see [04](04_match_shapes.md)).

## Why these choices

- **Share of strokes, not sessions passed:** it shows the effect of `sensitivity` and the session count directly,
  before the `match_shape_ratio` and `match_session_ratio` rules turn it into a yes/no.
- **Last 2 sessions as the legitimate test:** the pool holds 114–253 sessions per user, so the last ones are never
  in a profile of 1 … 10 sessions, and every run tests the **same** sessions. Taking "the next sessions after the
  profile" would test different sessions in every run.
- **Best profile for impostors:** the same rule the notebook uses (`best_profile`).

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
