# `02_sample_sessions.py`: draw the sessions of each chosen user

[← index](README.md) · previous: [01](01_sample_users.md) · next: [03](03_chunk_shapes.md)

## What it does

Step 2 of the single trial. For every user in the manifest, it decides which sessions to use:

- the first `sessions_per_user` sessions of the user's shuffled pool form the profile (legitimate users) or the
  test sessions (impostors);
- the remaining sessions are recorded as **held out**.

It copies the chosen files into `runs/<run>/temp/legitimate/<user>/` and `.../impostor/<user>/`, and adds the
lists to `manifest.json`.

## Algorithm

```
for label in (legitimate, impostor):
    delete temp/<label>/                        # clear only our own folders
    for user in manifest[label]:
        pool     ← session_pool(config, user, seed)   # see 00_config: training first, then test, each shuffled
        sessions ← pool[0 : k]                         # k = sessions_per_user
        held_out ← pool[k : ]
        copy every session file into temp/<label>/<user>/
        manifest["sessions"][label][user] = {sessions, held_out}
```

The method is a **prefix of a fixed random permutation** (a Fisher–Yates shuffle [[1]](#ref-1), [[2]](#ref-2)): the pool is shuffled once (seeded), and each user's
first *k* entries are taken.

## Why a prefix of one shuffle

- **Fair:** each session has the same chance of being chosen, so we are not always using the first file on disk.
- **Nested:** with a larger *k*, the profile only gains sessions; it never loses any. Comparing *k* = 3 with
  *k* = 4 therefore measures the effect of one more session and nothing else.
- **No overlap:** held-out sessions are never in the profile. Script 04 uses them as a sanity check: a user's
  own unseen sessions should match their profile better than impostors do.

## Checks

The script stops if `sessions_per_user` is larger than the smallest pool (`max_sessions`). Pools are 114–253
sessions (one merged folder per user).

## Input / output

- Input: `temp/manifest.json` from 01; `sessions_per_user`, `seed`.
- Output: copied session files in `temp/{legitimate,impostor}/<user>/`, plus the updated manifest.

## References

<a id="ref-1"></a>[1] R. Durstenfeld, "Algorithm 235: Random permutation," *Commun. ACM*, vol. 7, no. 7, p. 420, Jul. 1964, doi: [10.1145/364520.364540](https://doi.org/10.1145/364520.364540).

<a id="ref-2"></a>[2] Python Software Foundation, "random — Generate pseudo-random numbers," Python 3 documentation. [Online]. Available: https://docs.python.org/3/library/random.html
