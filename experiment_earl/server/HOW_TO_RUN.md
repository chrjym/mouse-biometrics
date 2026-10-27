# How to run simulation.ipynb on the server

This folder is the server copy of `experiment_earl/notebooks/earl_simulation.ipynb`: same simulation code and
settings, but it works from this layout (everything in the server's `experiment/` folder):

```
experiment/
├── simulation.ipynb, requirements.txt, HOW_TO_RUN.md, status.sh   (this folder)
└── experiment_earl/
    ├── datasets/balabit/     the Balabit data (step 1)
    ├── runs/                 results and logs (made by the notebook)
    └── cache/                DTW results reused across runs (made by the notebook)
```

Every command below runs **inside `experiment/`** on the server.

## 1. Copy the files (once)

From the repository root on your own computer:

```bash
scp experiment_earl/server/{simulation.ipynb,requirements.txt,HOW_TO_RUN.md,status.sh} <user>@<server>:experiment/
rsync -a experiment_earl/datasets <user>@<server>:experiment/experiment_earl/   # ~200 MB, once
```

Optional: `rsync -a experiment_earl/cache <user>@<server>:experiment/experiment_earl/` reuses the DTW results you
already computed locally (same settings only).

## 2. Python environment (once)

```bash
cd experiment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The server has Python 3.14, which needs **numba 0.63 or newer**; pip picks it. If you open the notebook with
another kernel, its first code cell installs whatever is missing into that kernel's Python.

## 3. Run it

Edit the **Settings** cell and save (`Ctrl+S`): a terminal run reads the saved file.

**Short runs:** open the notebook in Jupyter (`.venv/bin/jupyter lab --no-browser --port 8888`) and press Run All.

**Long runs** (keeps going after you close the browser or the terminal):

```bash
nohup .venv/bin/jupyter execute simulation.ipynb > experiment_earl/runs/notebook_run.log 2>&1 &
echo $! > experiment_earl/runs/notebook_run.pid
```

## 4. Follow it

```bash
tail -f experiment_earl/runs/notebook_progress.log   # everything the notebook prints, live; Ctrl+C stops watching
bash status.sh                                       # running or not, CPU/memory, error if it stopped, last lines
kill $(cat experiment_earl/runs/notebook_run.pid)    # stop early; finished runs are kept
```

With `SKIP_FINISHED_RUNS = True`, starting it again after a stop or a server restart simulates only the runs that
are not finished. Do not start two runs at once: they write the same files.

## 5. Results

`experiment_earl/runs/<hash>/`, as in the repository's `experiment_earl/notebooks/HOW_TO_RUN.md` (section 5). The
same `SETTINGS` give the same `<hash>` on the server and on your computer, so result folders can be copied back with
`rsync -a <user>@<server>:experiment/experiment_earl/runs/ experiment_earl/runs/`.

| Problem | What to do |
|---|---|
| `No Balabit data in .../experiment_earl/datasets/balabit` | Step 1, second command. |
| `pip could not install ...` | The kernel is the system Python (Ubuntu blocks pip there). Use the `.venv` of step 2. |
| `No such file or directory: .venv/bin/jupyter` | You are not in `experiment/`: `cd` there first. |
| Notebook opened from another folder | Set `EARL_HOME=/path/to/experiment` before starting Jupyter. |
