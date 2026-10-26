# `16_initial_results.py`: experiments 1 and 2 (initial results)

[← index](README.md) · previous: [15](15_best_setting.md)

## What it does

Reads `runs/<hash>/accuracy.csv` (written by [10](10_plot_accuracy.md)) and keeps the four fixed `splits` of
`config.yaml`. Each split is labelled `I x L` (impostor users x legitimate users). Run 10 first.

Outputs, in `runs/<hash>/initial_results/` (files are rewritten in place):

- `all_settings.csv`: every (split, sensitivity, sessions) cell of the four splits, with users through and sessions
  passed on each side, `legitimate_accuracy`, `impostor_accuracy`, `accuracy` and `session_accuracy`.
- `exp1_user_user_sensitivity.csv` / `.png`: experiment 1, 1 session per user, every sensitivity in the runs
  (0.01 … 1.00). Three panels: legitimate, impostor and mean accuracy against sensitivity, one line per split.
- `exp1_mean_over_experiments.csv`: mean accuracy over the splits per sensitivity; `exp1_best_sensitivity_per_experiment.csv`
  is the rows at the best one (highest mean accuracy, ties: session accuracy, then lower sensitivity).
- `exp2_user_session_sensitivity.csv` / `.png`: experiment 2, library sizes `initial_sessions` x sensitivities
  `initial_sensitivities`. Grid: one column per split, rows legitimate / impostor / mean accuracy against sessions,
  one line per sensitivity.

## Algorithm

Per cell, summed over the users of `accuracy.csv`:

- legitimate accuracy = legitimate users through / legitimate users;
- impostor accuracy = 1 − impostor users through / impostor users;
- accuracy = their mean (0.5 = chance); session accuracy = the same from sessions passed / tested.

The experiment 2 footnote is computed from the data: it lists the legitimate users tested on fewer than k sessions
(their pool has fewer than k sessions left after the library), and the sensitivities whose curves equal the highest
one's in every panel (they are hidden under its line).
