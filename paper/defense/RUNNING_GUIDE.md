# Running Guide (for the defense)

How to run the experiment live if the panel asks. Run every command from the **repository root** (`thesis-mouse-biometrics/`). On this laptop the `.venv` is already set up.

---

## 0. Before the defense (do once)

1. Back up the results the slides use, so a live re-run cannot change them:

   ```bash
   cp -r experiment_earl/runs/19399f/experiments experiment_earl/runs/19399f/experiments_backup
   ```

2. Check that the environment works:

   ```bash
   .venv/bin/python -c "import numba, pandas, matplotlib; print('ok')"
   ```

   If this fails, see section 6.

---

## 1. The manuscript's settings (important)

The notebook is currently set to **seed 946 with no labels file**. That is **not** the manuscript's run. To reproduce the manuscript (run `19399f`), set exactly these two values in the notebook's Settings cell:

```python
SETTINGS = {
    "seed": 945,
    ...
    "labels_file": "datasets/balabit/public_labels.csv",   # drops the 405 illegal sessions
    ...
}
```

Leave everything else in `SETTINGS` as it is (pause 0.5 s, min 10 points, 64 points, DTW band 0.1, 20% rule). With these values the results go to `experiment_earl/runs/19399f/` (checked: the settings hash is `19399f`).

---

## 2. Quick demo: Experiments 1 and 2 only

This re-creates the manuscript's Tables 3 and 4, reusing the 1,210 runs already in `runs/19399f/` and the DTW cache `experiment_earl/cache/costs_945.pkl`. Because nothing has to be recomputed it should be quick, but I have **not timed** it.

1. Open `experiment_earl/notebooks/earl_simulation.ipynb` in VS Code or Jupyter and pick the **.venv** kernel.
2. In the Settings cell, make the section 1 changes, then set:

   ```python
   MORE_SEEDS = []          # only seed 945

   SECTIONS = {
       "batch": False,
       "accuracy": False,
       "best": False,
       "sweep": False,
       "matches": False,
       "genuine_check": False,
       "experiments": True,  # 9. experiments 1 and 2
       "strokes": False,
   }
   ```

3. **Run All.**
4. Results in `experiment_earl/runs/19399f/experiments/`:

   | File | What to show | Expected value (manuscript) |
   |---|---|---|
   | `exp1_overall.csv` | the row with `best = True` | sensitivity **0.05**, TP 11, FP 6, FN 0, TN 5, accuracy **0.7273** |
   | `exp2_overall.csv` | the row with `best = True` | **5 sessions**, TP 6, FP 3, FN 49, TN 52, accuracy **0.5273** |
   | `exp1_points.csv`, `exp2_points.csv` | rows for one split | per-split rows of Tables 3 and 4 |
   | `exp1.png`, `exp2.png` | accuracy curves + confusion matrix | best 0.05 / best 5 sessions in the titles |

   Show the best rows from the terminal:

   ```bash
   grep -i true experiment_earl/runs/19399f/experiments/exp1_overall.csv
   grep -i true experiment_earl/runs/19399f/experiments/exp2_overall.csv
   ```

   The notebook rewrites `exp1.png`, `exp2.png` and the CSVs in that folder. It does not touch the group's own figures (`exp1_graph.png`, `exp1_confusion.png`, …). The backup from step 0 keeps the originals.

---

## 3. Full run (everything from the start)

Only if they ask to see the whole pipeline. Use the section 1 settings with all of `SECTIONS` set to `True` (keep `MORE_SEEDS = []`), then **Run All**.

- The batch is 4 splits × 100 sensitivities × 8 session counts = 3,200 runs, plus the sweep and the experiments.
- Measured earlier (2026-10-28, server copy, 2 cores, empty caches): about **9 minutes** for batch + sweep + experiments. With the runs and cache already on disk, finished runs are skipped (`SKIP_FINISHED_RUNS = True`).

### Run it in the background (from a terminal)

After saving the notebook with the settings above:

```bash
nohup .venv/bin/jupyter execute experiment_earl/notebooks/earl_simulation.ipynb > experiment_earl/runs/notebook_run.log 2>&1 &
echo $! > experiment_earl/runs/notebook_run.pid
```

Follow it:

```bash
tail -f experiment_earl/runs/notebook_progress.log      # live progress with an ETA
bash experiment_earl/notebooks/status.sh                # running or not, CPU, last lines, any error
```

---

## 4. Show the data numbers (Tables 1 and 2)

These one-liners recount the numbers on slides R1 and R2 from the data itself.

**Table 1: sessions, illegal removed, used per user** (expected total 1,676 / 405 / 1,271):

```bash
.venv/bin/python -c "
import pandas as pd, pathlib
lab = pd.read_csv('experiment_earl/datasets/balabit/public_labels.csv')
ill = set(lab.loc[lab.is_illegal == 1, 'filename'].astype(str))
t = r = 0
for u in sorted(pathlib.Path('experiment_earl/datasets/balabit/users').iterdir()):
    fs = [f.name for f in u.iterdir()]; n = sum(f in ill for f in fs); t += len(fs); r += n
    print(u.name, len(fs), n, len(fs) - n)
print('total', t, r, t - r)"
```

**Table 2: strokes per user, move / drag** (expected 109,948 = 106,320 move + 3,628 drag):

```bash
.venv/bin/python -c "
import pandas as pd
s = pd.read_csv('experiment_earl/runs/a6e6f7/strokes/all_strokes.csv', usecols=['user', 'kind', 'points', 'duration_s'])
print(s.groupby(['user', 'kind']).size().unstack()); print('total', len(s))
print('median points', s.points.median(), 'median duration (s)', s.duration_s.median())"
```

---

## 5. Re-draw the defense visuals

All in `paper/defense/`. They read the real data, so they need the repository's `experiment_earl/` folder.

| Output | Command |
|---|---|
| `figures/fig_m1_segmentation.png` (raw → strokes → normalized) | `.venv/bin/python paper/defense/make_segmentation_figure.py experiment_earl paper/defense/figures/fig_m1_segmentation.png` |
| `figures/process_overview_diagram.png`, `figures/two_experiments_diagram.png` (transparent) | `.venv/bin/python paper/defense/make_visual_pngs.py` |
| `figures/matching_dtw_diagram.png` (transparent) | `.venv/bin/python paper/defense/make_matching_png.py --experiment experiment_earl` |
| `process_overview.pptx` | `.venv/bin/python paper/defense/make_process_overview.py --template "paper/manuscript/Copy of THESIS PROPOSAL.pptx"` |
| `matching_dtw.pptx` | `.venv/bin/python paper/defense/make_matching_slide.py --template "paper/manuscript/Copy of THESIS PROPOSAL.pptx" --experiment experiment_earl` |
| `two_experiments.pptx` | `.venv/bin/python paper/defense/make_experiments_slide.py --template "paper/manuscript/Copy of THESIS PROPOSAL.pptx"` |

The `.pptx` scripts need `python-pptx` (installed in this laptop's `.venv`; elsewhere: `.venv/bin/pip install python-pptx`).

---

## 6. If something goes wrong

| Problem | Fix |
|---|---|
| `No module named 'numba'` (or pandas, …) | The wrong Python is running. Pick the **.venv** kernel in VS Code/Jupyter, or use `.venv/bin/python`. |
| `'RcParams' object has no attribute '_get'` when plotting | `.venv/bin/pip install "matplotlib-inline<0.2"`, then restart the kernel. |
| Results went to a different `runs/<hash>/` folder | `SETTINGS` differs from section 1 (usually the seed or `labels_file`). Fix it and run again. |
| Run stopped, `status.sh` shows an error | Read `experiment_earl/runs/notebook_run.log`. Run All again: finished runs are skipped. |
| Running out of memory with several seeds | Keep `MORE_SEEDS = []` for the defense. |
| Need the original results back | `cp -r experiment_earl/runs/19399f/experiments_backup/. experiment_earl/runs/19399f/experiments/` |
