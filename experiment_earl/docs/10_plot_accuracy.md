# `10_plot_accuracy.py`: how many sessions go through, per user, across runs

[← index](README.md) · previous: [09](09_genuine_check.md) · next: [12](12_pick_best.md)

## What it does

Compares every run inside one hash folder, `runs/<hash>/<n_legitimate>_<n_impostor>_<sensitivity>_<sessions_per_user>/`.
Runs in one hash folder share every other setting (seed, chunking, matching), so they differ only in those four values.
For each run it scores every drawn user with the notebook's fixed counts:

- **Legitimate users:** how many of their own last `sessions_per_user` sessions (never in a profile) go through their
  own profile.
- **Impostor users:** how many of their first `sessions_per_user` sessions (the ones the notebook tests) go through the
  legitimate profile that lets most of them through.

A user is through when at least `match_session_ratio` of the sessions go through.

Output (in the hash folder, not in a run): `runs/<hash>/accuracy.csv` (passed, tested, matched strokes, strokes,
through, best profile per run and user). No figures are drawn (the per-sensitivity PNGs were removed 2026-10-26).

## Algorithm

```
for each run folder under runs/<hash>/ (its own config.yaml snapshot):
    legitimate, impostors, order ← 08.draw_users(config, seed)       # the notebook's draw
    k ← sessions_per_user;  library[u] ← u's first k sessions
    legitimate u: test u's last k sessions of the pool against library[u]
    impostor v:   test v's first k sessions against every library[u]; keep the profile with most sessions passed
a session goes through  ⇔  matched_chunks(session, library) / strokes(session) ≥ match_shape_ratio
a user goes through     ⇔  sessions through ≥ match_session_ratio · k
```

## Formulas

$$\text{passed}(v, P) = \left|\left\{ s \in S_v : \frac{\text{matched\_chunks}(s, P)}{\text{strokes}(s)} \ge \texttt{match\_shape\_ratio} \right\}\right|$$

For an impostor $v$, the reported value is $\max_P \text{passed}(v, P)$ over the legitimate profiles $P$ (ties broken
by the share of strokes matched). A stroke matches when its banded DTW distance per point to some profile stroke is
at most `sensitivity` (see [04](04_match_shapes.md)).

## Why these choices

- **Fixed counts, the notebook's rules:** the impostor counts equal the notebook's `sessions_matched` column, and the
  filled impostor markers equal its "impostors matched" bar (checked on all 11 runs of `efdc92`).
- **Last k sessions as the legitimate test:** the pool holds 114–253 sessions per user, so the last ones are never
  in a profile of 1 … 10 sessions, and the legitimate user is tested on as many sessions as each impostor.
- **Best profile for impostors:** an impostor is matched when any legitimate profile lets them through.
- **Resumable:** each finished sensitivity is saved to `runs/<hash>/accuracy_parts/sensitivity_<value>.csv`. A
  rerun reuses every part whose runs match the folders now on disk and scores only the rest, so a kill loses at most
  the sensitivity in progress. A part is rescored when runs of that sensitivity were added or removed; delete
  `accuracy_parts/` to rescore everything (e.g. after changing the scoring code).
- **One sensitivity at a time:** runs are scored grouped by sensitivity, and the DTW pairs computed for a
  sensitivity are dropped once its group is done (the sensitivity is part of every cache key, so no later group
  could reuse them). Only the pairs at `config.yaml`'s current `sensitivity` are added to the shared cache. Keeping
  everything ran a 6,750-run hash folder (50 sensitivities) out of memory at ~5 GB. `accuracy.csv` is written before
  the cache is saved, so a failed save no longer loses the results.

## References

See [04_match_shapes.md](04_match_shapes.md) for the DTW matching and its references.
