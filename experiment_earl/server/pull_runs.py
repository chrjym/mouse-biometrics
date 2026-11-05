#!/usr/bin/env python3
"""Copy selected folders of every seed's runs/<hash>/ from the server, logging each copy so it is not repeated."""
import argparse
import csv
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE_RUNS = "experiment/experiment_earl/runs"
DEFAULT_FOLDERS = ["experiments", "sweep", "best", "summary", "accuracy.csv"]
LOG_FIELDS = ["time", "hash", "seed", "path", "kind", "files", "bytes", "newest"]

# Runs on the server (or locally): one line per selected path of each hash folder:
# hash, seed, path, kind (d/f), file count, total bytes, newest modification time (integer seconds).
LIST_SCRIPT = r'''
cd "$1" || { echo "no runs folder: $1" >&2; exit 2; }
shift
for d in */; do
  h=${d%/}
  [ -d "$h" ] || continue
  cfg=$(find "$h" -maxdepth 2 -name config.yaml -print -quit)
  seed=""
  [ -n "$cfg" ] && seed=$(sed -n 's/^seed:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$cfg" | head -n 1)
  for pat in "$@"; do
    for p in "$h"/$pat; do
      [ -e "$p" ] || continue
      if [ -d "$p" ]; then kind=d; else kind=f; fi
      stats=$(find "$p" -type f -printf '%s %T@\n' | awk '{n++; b+=$1; t=int($2); if (t>m) m=t} END {printf "%d\t%d\t%d", n, b, m}')
      printf '%s\t%s\t%s\t%s\t%s\n' "$h" "$seed" "${p#"$h"/}" "$kind" "$stats"
    done
  done
done
'''


def parse_seeds(items: list[str] | None) -> set[int] | None:
    """'946 950-960' -> {946, 950, ..., 960}; None keeps every seed."""
    if not items:
        return None
    seeds = set()
    for item in items:
        for part in item.split(","):
            low, _, high = part.partition("-")
            seeds.update(range(int(low), int(high or low) + 1))
    return seeds


def ssh_command(control: str) -> list[str]:
    """ssh that reuses one connection for the listing and every rsync."""
    return ["ssh", "-o", "ControlMaster=auto", "-o", f"ControlPath={control}", "-o", "ControlPersist=120"]


def list_source(remote: str | None, runs: str, folders: list[str], control: str) -> list[dict]:
    """Every selected path that exists under the source runs folder, with its fingerprint."""
    if remote:
        remote_cmd = "bash -s -- " + " ".join(shlex.quote(a) for a in [runs, *folders])
        cmd = [*ssh_command(control), remote, remote_cmd]
    else:
        cmd = ["bash", "-s", "--", runs, *folders]
    out = subprocess.run(cmd, input=LIST_SCRIPT, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"listing failed ({out.returncode}): {out.stderr.strip()}")
    rows = []
    for line in out.stdout.splitlines():
        h, seed, path, kind, files, size, newest = line.split("\t")
        rows.append({"hash": h, "seed": seed, "path": path, "kind": kind,
                     "files": files, "bytes": size, "newest": newest})
    return rows


def read_log(log: Path) -> dict[tuple[str, str], dict]:
    """Last logged copy of each (hash, path)."""
    if not log.exists():
        return {}
    with log.open(newline="") as f:
        return {(r["hash"], r["path"]): r for r in csv.DictReader(f)}


def append_log(log: Path, row: dict) -> None:
    new = not log.exists()
    with log.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            writer.writeheader()
        writer.writerow({k: row[k] for k in LOG_FIELDS})


def same(row: dict, logged: dict | None) -> bool:
    return logged is not None and all(row[k] == logged[k] for k in ("files", "bytes", "newest"))


def local_stats(path: Path) -> tuple[int, int]:
    files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def copy(row: dict, remote: str | None, runs: str, dest: Path, control: str) -> str | None:
    """rsync one path; returns an error message or None."""
    rel = f"{row['hash']}/{row['path']}"
    target = dest / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    source = f"{runs.rstrip('/')}/{rel}"
    if remote:
        source = f"{remote}:{shlex.quote(source)}"
    slash = "/" if row["kind"] == "d" else ""
    cmd = ["rsync", "-a", "--partial"]
    if remote:
        cmd += ["-e", " ".join(ssh_command(control))]
    out = subprocess.run([*cmd, source + slash, str(target) + slash], capture_output=True, text=True)
    if out.returncode != 0:
        return f"rsync {out.returncode}: {out.stderr.strip()}"
    files, size = local_stats(target)
    if (files, size) != (int(row["files"]), int(row["bytes"])):
        return f"size check failed: local {files} files / {size} B, source {row['files']} files / {row['bytes']} B"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", help="user@server; leave out to copy from a local or mounted folder")
    parser.add_argument("--source", default=None,
                        help=f"runs folder at the source (default with --remote: {DEFAULT_REMOTE_RUNS})")
    parser.add_argument("--folders", nargs="+", default=DEFAULT_FOLDERS,
                        help="paths inside each runs/<hash>/, globs allowed, e.g. experiments sweep '1_5_*' "
                             f"(default: {' '.join(DEFAULT_FOLDERS)})")
    parser.add_argument("--seeds", nargs="+", help="only these seeds, e.g. 946 950-960 (default: all)")
    parser.add_argument("--dest", type=Path, default=ROOT / "runs", help="local runs folder (default: experiment_earl/runs)")
    parser.add_argument("--log", type=Path, default=None, help="copy log (default: <dest>/pull_log.csv)")
    parser.add_argument("--dry-run", action="store_true", help="only print what would be copied")
    args = parser.parse_args()

    runs = args.source or (DEFAULT_REMOTE_RUNS if args.remote else None)
    if runs is None:
        parser.error("give --remote user@server, or --source <folder> for a local copy")
    log = args.log or args.dest / "pull_log.csv"
    seeds = parse_seeds(args.seeds)
    control = os.path.join(tempfile.gettempdir(), f"pull_runs_{os.getuid()}_%C")

    rows = list_source(args.remote, runs, args.folders, control)
    if seeds is not None:
        rows = [r for r in rows if r["seed"].isdigit() and int(r["seed"]) in seeds]
    logged = read_log(log)
    todo = [r for r in rows if not same(r, logged.get((r["hash"], r["path"])))]
    found = {r["seed"] or "?" for r in rows}
    print(f"{len(rows):,} paths found in {len({r['hash'] for r in rows}):,} hash folders ({len(found):,} seeds), "
          f"{len(rows) - len(todo):,} already copied, {len(todo):,} to copy")

    copied, failed, total = 0, 0, 0
    for i, row in enumerate(todo, 1):
        label = f"[{i}/{len(todo)}] seed {row['seed'] or '?'} {row['hash']}/{row['path']} ({int(row['bytes']) / 1e6:.1f} MB)"
        if args.dry_run:
            print("would copy", label)
            continue
        error = copy(row, args.remote, runs, args.dest, control)
        if error:
            failed += 1
            print("FAILED", label, "-", error, flush=True)
            continue
        append_log(log, {**row, "time": datetime.now().isoformat(timespec="seconds")})
        copied += 1
        total += int(row["bytes"])
        print("ok", label, flush=True)

    if not args.dry_run:
        print(f"copied {copied:,} paths ({total / 1e6:.1f} MB), {failed:,} failed -> {args.dest}; log {log}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
