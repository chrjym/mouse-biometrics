# `18_best_setting.py`: best sensitivity and library size per user

[← index](README.md) · previous: [17](17_plot_sweep.md)

## What it does

Answers "at which sensitivity and with how many sessions should a given user be profiled?" from
`runs/<hash>/sweep/user_confusion.csv` (written by [16](16_sweep_sensitivity.md)), without scoring the choice on the
sessions it was chosen on.

- 16 counts one confusion matrix per (legitimate user, sessions, sensitivity): the user's own 40 test sessions and
  every impostor attempt against that user's library. Test sessions alternate between two halves: even = **pick**,
  odd = **check**.
- 18 picks, per user and per split, the setting with the highest balanced accuracy on the pick half (ties: fewer
  sessions, then lower sensitivity), and reports the same setting's scores on the check half unchanged.

Outputs in `runs/<hash>/sweep/best/`: `best_users.csv`, `best_splits.csv` (pick- and check-half TP/FP/FN/TN, FAR,
FRR, balanced accuracy) and `best_users.png` (pick half hollow, check half filled, one row per user).

## Algorithm

```
for each (split, legitimate user):            # per split: the users' counts summed
    pick half:  BA(s, k) for every sensitivity s and library size k
    best = argmax BA; ties → fewer sessions, then lower s
    check half: TP / FP / FN / TN at best, unchanged
```

## Reading it

The check half is the honest number: the pick half is the highest of 4,000 settings and is always optimistic.
A user whose check score stays near the pick score has a setting that holds on unseen sessions; a large drop
(e.g. to 0.5) means the "best" was luck. In seed 945 every high score comes from the 5 L × 1 I split, whose only
impostor is user16, so those scores say how well each profile rejects user16, not impostors in general.
