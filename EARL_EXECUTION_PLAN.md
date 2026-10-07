# EARL experiment: execution plan (Balabit only)

**Decisions locked in:** pause-based chunking, resample + DTW matching, a "match" means an impostor matches a legitimate profile (a false accept, so lower is better), and impostors are other users' sessions (`public_labels` ignored).

**Two assumptions to confirm or correct:**
- **A1.** `matched_detected` counts **impostor users**, because the formula divides by `total_impostor_user`. An impostor user counts as "matched" when enough of their sessions match the legitimate profile. The cut-off is configurable (`match_session_ratio`, default 0.5).
- **A2.** A session counts as matched when at least `match_shape_ratio` (default 0.3) of its shapes match a shape in the legitimate library.

## Project layout

```
experiment_earl/
├── config.yaml
├── datasets/balabit/{training_files,test_files}/userX/session_NNNN
├── temp/
│   ├── legitimate/<user>/<session>        # raw session copies
│   ├── impostor/<user>/<session>
│   └── manifest.json                      # who was drawn, with seed
├── shapes/{legitimate,impostor}/<user>/<session>.npz   # chunked trajectories
├── results/trial_*.json, summary.csv
├── figures/bar_matched.png, heatmap.png
└── src/
    ├── 00_config.py
    ├── 01_sample_users.py
    ├── 02_sample_sessions.py
    ├── 03_chunk_shapes.py
    ├── 04_match_shapes.py
    ├── 05_threshold.py
    ├── 06_plot_bar.py
    └── 07_plot_heatmap.py
```

Use **one config file** shared by all scripts:

```yaml
seed: 42
n_legitimate: 3
n_impostor: 10
sessions_per_user: 5
pause_gap_s: 0.5
min_points: 10
resample_n: 64
dtw_tolerance: 0.15
match_shape_ratio: 0.3
match_session_ratio: 0.5
n_trials: 20
grid_sessions: [1,2,3,4,5]
grid_legit_users: [1,2,3,4,5]
```

---

## Phase 1: Data preparation and sampling (draft steps 1, 3, 4)

**Step 1.1: Dataset loader (`00_config.py`).**
- Load `config.yaml` and expose a `load_session(path) -> DataFrame` helper.
- Balabit session files are CSVs with columns `record timestamp, client timestamp, button, state, x, y`.
- Keep only `client timestamp`, `x`, `y`, `button`, `state`. Rename them to `t, x, y, button, state`.
- Convert `t` to float seconds relative to the first event.
- Drop rows with NaN coordinates.
- Treat `Scroll` events as non-trajectory events, because they carry no path.

**Step 1.2: Random user selection (`01_sample_users.py`).**
- Inputs: the config and the list of `userX` folders in `datasets/balabit/training_files`.
- Seed `random.Random(seed)`.
- Draw `n_legitimate` users, then draw `n_impostor` users from the remaining pool. The two sets must not overlap.
- Output: `temp/manifest.json` with `{"seed":..., "legitimate":[...], "impostor":[...]}`.
- Edge case: if `n_legitimate + n_impostor` is larger than the number of users, stop with a clear error.

**Step 1.3: Random session selection (`02_sample_sessions.py`).**
- For each user in the manifest, list session files and randomly choose `sessions_per_user` (or all of them, if fewer exist).
- Copy each chosen file to:
  - `temp/legitimate/<user>/<session name>` for legitimate users
  - `temp/impostor/<user>/<session name>` for impostor users
- Record the chosen session names back into `manifest.json`.
- Clear `temp/` at the start of each run so trials never mix.

**Data flow:** `datasets/` → `01` → `manifest.json` → `02` → `temp/`.

---

## Phase 2: Feature extraction and chunking (draft step 2)

**Step 2.1: Define a trajectory.**
A trajectory is an array of shape `(N, 3)` holding `[x, y, timestamp]`. Never modify the original values; the idea requires conserving them.

**Step 2.2: Pause-based segmentation (`03_chunk_shapes.py`).**
For every session under `temp/`:
1. Sort rows by `t`.
2. Compute `dt = t[i] - t[i-1]`.
3. Start a new chunk whenever `dt > pause_gap_s`.
4. Also start a new chunk on every `Pressed` or `Released` state, so click and drag actions stay separate from free movement.
5. Discard chunks with fewer than `min_points` points (single jitters are not shapes).
6. Save the raw chunks unchanged.

**Step 2.3: Per-chunk descriptor (for matching, not stored over raw data).**
Compute these at match time or store them alongside the raw chunk:
- **Normalized path:** translate so the start point is the origin, divide by the bounding-box diagonal (scale invariance), and resample to `resample_n` points by arc length.
- **Optional metadata:** total length, duration, mean speed, and type (`move` or `drag`). Used for logging and for restricting comparisons to chunks of the same type.

**Step 2.4: Output.**
- `shapes/<class>/<user>/<session>.npz` with arrays `chunk_0, chunk_1, …` (raw `[x, y, t]`) and a `meta` array.
- Print a summary per user: sessions, chunks, and average chunk length.
- This is the "set of unique shapes per user" from the draft. Sessions are kept whole in `temp/`, and the chunks are an additional export.

**Step 2.5: Build the legitimate library.**
For each legitimate user, the library is the union of all normalized chunks from their sessions. Save it as `shapes/legitimate/<user>/library.npz`.

---

## Phase 3: Trajectory matching and threshold (draft steps 5 and 6)

**Step 3.1: Pairwise distance (`04_match_shapes.py`).**
- Use the DTW distance between two normalized `(resample_n, 2)` paths, with a Sakoe-Chiba band of about 10% to keep it fast. A pure-NumPy implementation or `fastdtw`/`tslearn` both work.
- Divide by `resample_n` so the distance is comparable across chunks.
- Two chunks "match" if `dtw <= dtw_tolerance`.

**Step 3.2: Match one impostor session against one legitimate user.**
```
for each chunk c in impostor_session:
    matched = any(dtw(c, L) <= tol for L in legit_library)   # same type only
session_match_ratio = matched_chunks / total_chunks
session_is_matched  = session_match_ratio >= match_shape_ratio     # A2
```
All chunks stay in the denominator (every recorded line still counts).

**Step 3.3: Impostor-user decision.**
```
user_is_matched = (matched_sessions / total_sessions) >= match_session_ratio   # A1
```

**Step 3.4: Aggregate across the legitimate users.**
For each impostor user, an impostor is counted as `matched` if they match **any** selected legitimate profile. Write one record per impostor user to `results/trial_k.json`:
```json
{"impostor":"user12","matched":true,"matched_against":"user7","session_ratios":[0.4,0.1,0.5]}
```

**Step 3.5: Threshold (`05_threshold.py`).**
```
matched_detected = count(records where matched == true)
total_impostor_user = n_impostor
threshold = matched_detected / total_impostor_user
```
- Result is in [0, 1]. Closer to 0 means impostors rarely look like the legitimate user, so shapes are unique.
- Append each trial to `results/summary.csv` with columns `trial, n_legit, n_sessions, n_impostor, matched_detected, threshold`.

**Step 3.6: Performance and sanity checks.**
- Cache normalized chunks so each is computed once.
- Cap or subsample very large libraries if runtime gets long.
- As a sanity check, match a legitimate user's own held-out session against their library. The ratio should be clearly higher than for impostors; if not, adjust `dtw_tolerance`. This check only validates the tolerance and does not change the pipeline.

---

## Phase 4: Visualization and evaluation (draft steps 7 and 8)

**Step 4.1: Bar graph (`06_plot_bar.py`).**
- Use matplotlib.
- Horizontal axis: `total_number_impostor_user` (for example 5, 10, 15, 20).
- Vertical axis: `matched_detected` (mean across trials, with optional error bars from the standard deviation).
- To get the horizontal values, rerun Phase 1 to 3 with different `n_impostor` values, holding the other parameters fixed.
- Label each bar with its value and save to `figures/bar_matched.png`.

**Step 4.2: Heatmap experiment grid (`07_plot_heatmap.py`).**
For every combination in `grid_sessions × grid_legit_users`:
1. Set `sessions_per_user` and `n_legitimate` from the grid cell, and keep `n_impostor` fixed.
2. Run the whole pipeline for `n_trials` random draws with different seeds.
3. Cell value = mean of `threshold` across the trials.

**Step 4.3: Render.**
- Vertical axis: number of sessions.
- Horizontal axis: number of legitimate users.
- Color scale fixed to 0.0 to 1.0 with discrete steps of 0.1 (`BoundaryNorm` with levels `0.0, 0.1, …, 1.0`).
- Use a sequential colormap where 0 is the best color, and annotate each cell with its value.
- Save to `figures/heatmap.png` and the matrix to `results/heatmap_matrix.csv`.

**Step 4.4: Evaluation notes.**
- Report the mean and standard deviation per cell so you can see how stable the random draws are.
- Always log the seed and config used for each figure so results are reproducible.

---

## Suggested run order

```
python src/01_sample_users.py
python src/02_sample_sessions.py
python src/03_chunk_shapes.py
python src/04_match_shapes.py
python src/05_threshold.py
python src/06_plot_bar.py
python src/07_plot_heatmap.py     # loops the pipeline over the grid
```

## Open items for clarification

- The defaults for A1 and A2.
- The `dtw_tolerance` of 0.15, which will need tuning on real data.
- The number of impostors for the bar graph's horizontal values.
