#!/usr/bin/env python3
"""Run every notebook run of batch.yaml for one member: set config.yaml per run, skip finished runs, log, restore."""

import argparse
import csv
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from importlib import import_module
from pathlib import Path

import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
BACKUP = ROOT / "config.yaml.batch-backup"
LOG = cfg_mod.RUNS / "batch_log.csv"
DONE_MARKER = Path("results") / "session_progression.csv"


def plan_runs(plan: dict, member: str, only: float | None) -> list[dict]:
    """Every (split, sensitivity, sessions) assigned to `member`, as config overrides."""
    if member not in plan["assign"]:
        raise SystemExit(f"No member {member!r} in batch.yaml; members: {', '.join(plan['assign'])}")
    return [{"seed": plan["seed"], "n_legitimate": legit, "n_impostor": impostor,
             "sensitivity": sensitivity, "sessions_per_user": sessions}
            for legit, impostor in plan["assign"][member]
            for sensitivity in plan["sensitivities"] if only is None or sensitivity == only
            for sessions in plan["sessions"]]


def set_values(text: str, overrides: dict) -> str:
    """Replace each `key: value` line of config.yaml, keeping its comment."""
    for key, value in overrides.items():
        text, count = re.subn(rf"^({key}:\s*)\S+", rf"\g<1>{value}", text, count=1, flags=re.MULTILINE)
        if count != 1:
            raise SystemExit(f"config.yaml has no line '{key}: ...'")
    return text


def log_row(row: dict) -> None:
    new = not LOG.exists()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if new:
            writer.writeheader()
        writer.writerow(row)


def run_one(overrides: dict, original: str, timeout: int) -> tuple[str, str]:
    """Write the run's config, execute the notebook, return (status, error)."""
    CONFIG.write_text(set_values(original, overrides))
    try:
        result = subprocess.run([sys.executable, str(ROOT / "src" / "08_run_notebook.py"), "--timeout", str(timeout)],
                                cwd=ROOT.parent, capture_output=True, text=True)
    except OSError as error:
        return "failed", str(error)
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        return "failed", lines[-1] if lines else f"exit code {result.returncode}"
    return "ok", ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member", required=True, help="member in batch.yaml's assign (e.g. A or B)")
    parser.add_argument("--plan", type=Path, default=ROOT / "batch.yaml", help="batch plan file")
    parser.add_argument("--only", type=float, help="run a single sensitivity, e.g. 0.2 (quick test)")
    parser.add_argument("--dry-run", action="store_true", help="list the runs and whether each is done, run nothing")
    parser.add_argument("--timeout", type=int, default=3600, help="seconds allowed per notebook run")
    args = parser.parse_args()

    runs = plan_runs(yaml.safe_load(args.plan.read_text()), args.member, args.only)
    if BACKUP.exists():
        raise SystemExit(f"{BACKUP} exists: an earlier batch did not finish cleanly. Check config.yaml, "
                         f"restore it from the backup if needed, then delete the backup.")
    original = CONFIG.read_text()
    shutil.copy2(CONFIG, BACKUP)
    counts = {"ok": 0, "skipped": 0, "failed": 0}
    new_folders = []
    try:
        for i, overrides in enumerate(runs, 1):
            name = cfg_mod.run_folder_name(cfg_mod.load_config(**overrides))
            folder = cfg_mod.RUNS / name
            prefix = f"[{i}/{len(runs)}] {name}"
            if (folder / DONE_MARKER).exists():
                counts["skipped"] += 1
                print(f"{prefix} ... done already, skipped")
                continue
            if args.dry_run:
                print(f"{prefix} ... to run")
                continue
            print(f"{prefix} ...", end=" ", flush=True)
            start = time.monotonic()
            status, error = run_one(overrides, original, args.timeout)
            seconds = round(time.monotonic() - start)
            counts[status] += 1
            if status == "ok":
                new_folders.append(name)
            print(f"{status} ({seconds // 60}m {seconds % 60:02d}s){'  ' + error if error else ''}")
            log_row({"time": datetime.now().isoformat(timespec="seconds"), "member": args.member, "run": name,
                     "status": status, "seconds": seconds, "error": error})
    finally:
        CONFIG.write_text(original)
        BACKUP.unlink()

    to_run = len(runs) - counts["skipped"]
    if args.dry_run:
        print(f"\nDry run: {len(runs)} runs for member {args.member}, {counts['skipped']} done, {to_run} to run.")
        return
    print(f"\nMember {args.member}: {counts['ok']} ok, {counts['skipped']} skipped, {counts['failed']} failed "
          f"of {len(runs)}. config.yaml restored. Log: {LOG}")
    if counts["failed"]:
        print("Failed runs are listed in the log; rerun the same command to retry only those.")
    if new_folders:
        print("\nTo share the new runs (runs/ is git-ignored, so -f is needed):")
        print("  git add -f " + " ".join(f"experiment_earl/runs/{name}" for name in new_folders))


if __name__ == "__main__":
    main()
