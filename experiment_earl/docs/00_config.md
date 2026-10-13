# `00_config.py`: settings, run folders and the session loader

[← index](README.md)

## What it is

A shared module, not a step. All other scripts load it with `import_module("00_config")`; the number in the
name prevents a plain `import`. It does four jobs:

1. reads `config.yaml`;
2. chooses the **run folder** where a script writes its results;
3. decides which sessions belong to a user and in which order;
4. loads one raw Balabit file and cleans it.

## 1. Loading the config

`load_config()` reads the YAML file into a dictionary. Keyword overrides, when given, replace values in that
dictionary. Every number used by the experiment comes from this dictionary. No script hardcodes one.

## 2. Run folders: one folder per configuration

**Algorithm (`run_folder_name`, `open_run`)**

1. Take every setting except `run_name`.
2. Turn the settings into a JSON string with the keys sorted, so the same settings always give the same string.
3. Hash the string with **SHA-1** and keep the first 6 hexadecimal characters.
4. The folder is `runs/<run_name>_<hash>/`. If it does not exist yet, create it and save a copy of
   `config.yaml` there, plus `run.json` (creation time and the current git commit).
5. With `--run <folder>`, or the `EARL_RUN` environment variable, open that existing folder and use **its**
   saved `config.yaml`, not the current one.

$$\text{folder} = \text{run\_name} \;\|\; \text{"\_"} \;\|\; \text{SHA1}(\text{JSON}_\text{sorted}(\text{settings} \setminus \text{run\_name}))_{[0:6]}$$

**Why a hash?** We change settings often (tolerance, number of users, seed). If every script wrote to a fixed
`results/` folder, a new run would overwrite the old one, and we could not tell which settings produced a
figure. The hash ties each set of results to the exact settings that produced it:

- the same settings give the same folder, so a rerun continues the same experiment;
- different settings give a new folder, so older results are kept.

SHA-1 is used only as a fingerprint here, not for security. Six hex characters give 16.7 million possible
values, far more than the number of runs we will ever make.

## 3. Which sessions belong to a user, and in what order

**Rule (adviser + group decision, 2026-10-08):** a session belongs to the user whose folder it is in. This holds
for training files and test files alike, and `public_labels.csv` is not used.

**Algorithm (`session_pool(config, user, seed)`)**

1. `train` = the user's files in `training_files/<user>/`, sorted by name.
2. `test` = the user's files in `test_files/<user>/`, but only if `use_test_files` is true.
3. If a `seed` is given, shuffle each list separately, each with its own random generator:
   `Random(f"{seed}-{user}")` for training and `Random(f"{seed}-{user}-test")` for test.
4. Return training sessions first, then test sessions, as `(folder, name)` pairs.

**Why shuffle each part separately and put training first?** Balabit training sessions are long and test
sessions are often short (a few dozen strokes). Putting training sessions first means the first profile
sessions are the informative ones.

**Why seed the generator with a string that includes the user?** Three reasons:

- the same seed always gives the same order (the run can be reproduced);
- each user's order is independent of the others;
- adding or removing users does not change anyone else's order.

**Why is the order nested?** Taking "the first *k* sessions" of a fixed order means step *k + 1* contains
everything in step *k* plus one session. When results change between steps, the cause is the extra session and
not a different random draw.

`max_sessions()` = the smallest pool size over all users, i.e. the largest *k* every user can supply.

## 4. Loading and cleaning a session (`load_session`)

A raw Balabit row is `record timestamp, client timestamp, button, state, x, y`.

**Algorithm**

1. Read only `client timestamp, button, state, x, y` and rename the timestamp to `t`.
2. Drop rows with a missing `t`, `x` or `y`.
3. Drop **scroll** rows. They record wheel events, not a pointer path.
4. Drop **glitch** rows where `x` or `y` is 65535 (`INVALID_COORDINATE`). 65535 = 2¹⁶ − 1, the largest 16-bit
   value. It is a logging error, not a position, and keeping it would create jumps of about 60,000 px.
5. Sort by `t` with a **stable** sort (`kind="stable"`).
6. Shift time so the first event is at $t = 0$: $t_i \leftarrow t_i - t_1$.

**Why a stable sort?** Many Balabit timestamps are equal. A stable sort keeps tied rows in file order, which is
the order they were logged in. Pandas' default sort is not stable and can swap tied rows, which reverses tiny
pieces of the path.

**Why `client timestamp`?** It has about 16 ms resolution, while `record timestamp` has about 0.1 s.

## Settings used

`run_name`, `seed`, `dataset_dir`, `test_dir`, `use_test_files`.
