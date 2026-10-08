"""Shared config and Balabit session loader for the EARL shape-matching experiment."""

import csv
import hashlib
import json
import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"        # one folder per config: config.yaml, results/, figures/, shapes/, temp/, notebooks/
CACHE_DIR = ROOT / "cache"  # DTW pair cache shared by all runs (its keys hold the settings that change a score)
INVALID_COORDINATE = 65535  # Balabit logging glitch, not a position


def load_config(path: Path | None = None, **overrides) -> dict:
    with (path or ROOT / "config.yaml").open() as handle:
        config = yaml.safe_load(handle)
    config.update(overrides)
    return config


def run_folder_name(config: dict) -> str:
    """`<run_name or tol/gap/n>_<hash>`: the same settings always give the same folder, any change gives a new one."""
    settings = {k: v for k, v in config.items() if k != "run_name"}
    digest = hashlib.sha1(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:6]
    label = config.get("run_name") or f"tol{config['dtw_tolerance']}_gap{config['pause_gap_s']}_n{config['resample_n']}"
    return f"{label}_{digest}"


def add_run_argument(parser) -> None:
    parser.add_argument("--run", help="name of an existing folder under runs/ to read and write instead of "
                                      "the one config.yaml selects")


def open_run(run: str | None = None) -> tuple[dict, Path]:
    """Config and run folder. Without `run`, the current config.yaml picks (or creates) its folder and is
    saved there as a snapshot; with `run`, that folder's own snapshot is used."""
    run = run or os.environ.get("EARL_RUN")
    if run:
        folder = RUNS / run
        if not (folder / "config.yaml").exists():
            known = ", ".join(sorted(p.name for p in RUNS.iterdir())) if RUNS.exists() else "none"
            raise SystemExit(f"No run {run!r} under {RUNS}; existing runs: {known}")
        return load_config(folder / "config.yaml"), folder
    config = load_config()
    folder = RUNS / run_folder_name(config)
    if not folder.exists():
        folder.mkdir(parents=True)
        shutil.copy2(ROOT / "config.yaml", folder / "config.yaml")
        try:
            commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                    cwd=ROOT, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            commit = None
        (folder / "run.json").write_text(json.dumps(
            {"created": datetime.now().isoformat(timespec="seconds"), "git_commit": commit}, indent=2) + "\n")
        print(f"New run folder: {folder}")
    return config, folder


def list_users(config: dict) -> list[str]:
    return sorted(p.name for p in (ROOT / config["dataset_dir"]).iterdir() if p.is_dir())


def list_sessions(config: dict, user: str) -> list[Path]:
    """The user's training sessions only."""
    return sorted(p for p in (ROOT / config["dataset_dir"] / user).iterdir() if p.is_file())


_LABELS: dict = {}


def load_labels(config: dict) -> dict[str, int]:
    """Test session name -> is_illegal (0 = genuine, 1 = impostor). Unlabeled sessions are missing."""
    path = ROOT / config["labels_file"]
    if path not in _LABELS:
        with path.open(newline="") as handle:
            _LABELS[path] = {row["filename"]: int(row["is_illegal"]) for row in csv.DictReader(handle)}
    return _LABELS[path]


def _test_sessions(config: dict, user: str, label: int | None) -> list[str]:
    """Test sessions in `user`'s folder with this label (None = unlabeled)."""
    labels = load_labels(config)
    folder = ROOT / config["test_dir"] / user
    return sorted(p.name for p in folder.iterdir() if labels.get(p.name) == label) if folder.exists() else []


def session_pool(config: dict, user: str, seed: int | None = None) -> list[tuple[str, str]]:
    """(folder, session name) of every session counted as `user`'s, in this order: training sessions; with
    `test_genuine_sessions`, test sessions Balabit labels genuine; with `test_unlabeled_sessions`, unlabeled test
    sessions in the user's folder (assumed to be the folder's user). With `seed`, each part is shuffled on its own,
    so the verified sessions always come first and step k+1 contains step k."""
    train = [p.name for p in list_sessions(config, user)]
    genuine = _test_sessions(config, user, 0) if config.get("test_genuine_sessions") else []
    unlabeled = _test_sessions(config, user, None) if config.get("test_unlabeled_sessions") else []
    if seed is not None:
        random.Random(f"{seed}-{user}").shuffle(train)
        random.Random(f"{seed}-{user}-test").shuffle(genuine)
        random.Random(f"{seed}-{user}-unlabeled").shuffle(unlabeled)
    return [(config["dataset_dir"], n) for n in train] + [(config["test_dir"], n) for n in genuine + unlabeled]


def impostor_attempts(config: dict, user: str) -> list[str]:
    """Test sessions in `user`'s folder that Balabit labels impostor: someone else posing as `user`
    (empty unless `test_impostor_attempts`)."""
    return _test_sessions(config, user, 1) if config.get("test_impostor_attempts") else []


def max_sessions(config: dict) -> int:
    """Largest session count every user can supply."""
    return min(len(session_pool(config, user)) for user in list_users(config))


def describe_data(config: dict) -> str:
    users = list_users(config)
    train = sum(len(list_sessions(config, u)) for u in users)
    genuine = sum(len(_test_sessions(config, u, 0)) for u in users)
    impostor = sum(len(_test_sessions(config, u, 1)) for u in users)
    unlabeled = sum(len(_test_sessions(config, u, None)) for u in users)
    used = lambda key: "used" if config.get(key) else "not used"
    unlabeled_use = "assumed to be the folder's user" if config.get("test_unlabeled_sessions") else "left out"
    return (f"Data (labels from {config['labels_file']}): {len(users)} users, {train} training sessions; "
            f"test files: {genuine} labeled genuine ({used('test_genuine_sessions')}), "
            f"{impostor} labeled impostor ({used('test_impostor_attempts')}), "
            f"{unlabeled} unlabeled ({unlabeled_use}); at most {max_sessions(config)} sessions per user")


def load_session(path: Path) -> pd.DataFrame:
    """Columns t (seconds from the first event), x, y, button, state, in time order.

    Scroll rows carry no path and glitch rows (x or y = 65535) are not positions, so both are dropped.
    The sort is stable because many Balabit timestamps tie.
    """
    df = pd.read_csv(path, usecols=["client timestamp", "button", "state", "x", "y"])
    df = df.rename(columns={"client timestamp": "t"})
    df = df.dropna(subset=["t", "x", "y"])
    df = df[(df["button"] != "Scroll") & (df["x"] < INVALID_COORDINATE) & (df["y"] < INVALID_COORDINATE)]
    df = df.sort_values("t", kind="stable").reset_index(drop=True)
    df["t"] = df["t"] - df["t"].iloc[0] if len(df) else df["t"]
    return df[["t", "x", "y", "button", "state"]]
