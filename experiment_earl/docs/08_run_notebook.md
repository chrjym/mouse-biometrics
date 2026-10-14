# `08_run_notebook.py`: execute the session-progression notebook for a run

[← index](README.md)

## What it does

Runs `notebooks/session_progression.ipynb` from top to bottom without opening Jupyter [[1]](#ref-1), and saves the executed
copy (with all outputs and plots) as `runs/<run>/notebooks/session_progression.ipynb`.

## Algorithm

```
config, run ← open_run(--run)                  # same run-folder rule as every script
set EARL_RUN = run name                        # the notebook reads this, so it uses the same folder
notebook ← read the template notebook
run every cell with nbconvert's ExecutePreprocessor (python3 kernel, working dir = notebooks/, --timeout s)
write the executed notebook into the run folder
```

## Why

- **The template stays clean.** The notebook in `notebooks/` is never overwritten with outputs, so git diffs show
  only code changes.
- **Results stay with their settings.** The executed copy is saved next to the run's `config.yaml`, like every
  other result.

## What the notebook computes

The notebook is a **self-contained copy** of the 00–05 logic. Changes in `src/` do not reach it, and changes in
the notebook do not reach `src/`.

One draw from `seed` fixes `n_legitimate` legitimate users, `n_impostor` impostors, and every user's session
order. For sessions per user $k = 1 \dots$ `sessions_per_user` (nested), it counts how many impostors match
each legitimate profile, using the rules of [04](04_match_shapes.md). It draws:

- a bar chart of impostors matched;
- the same count, one panel per legitimate user;
- a heatmap of the threshold, using the first 1 … `n_legitimate` legitimate users.

Script [14](14_plot_matches.md) and script [15](15_genuine_check.md) reproduce its draw.

## References

<a id="ref-1"></a>[1] Jupyter developers, "Executing notebooks," nbconvert documentation. [Online]. Available: https://nbconvert.readthedocs.io/en/latest/execute_api.html
