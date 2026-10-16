#!/usr/bin/env python3
"""Run every notebook run of batch.yaml (skip finished runs, log), then plot them. config.yaml is never changed:
each run gets its own snapshot (config.yaml with the batch.yaml values) in its run folder."""

import argparse
import csv
import re
import subprocess
import sys
import time
from datetime import datetime
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.yaml"
LOG = cfg_mod.RUNS / "batch_log.csv"
DONE_MARKER = Path("results") / "session_progression.csv"


def plan_runs(plan: dict, only: float | None) -> list[dict]:
    """Every (split, sensitivity, sessions) of the plan, as config overrides."""
    for legit, impostor in plan["splits"]:
        if legit + impostor > 10:
            raise SystemExit(f"Split [{legit}, {impostor}] needs {legit + impostor} users; Balabit has 10")
    return [{"seed": plan["seed"], "n_legitimate": legit, "n_impostor": impostor,
             "sensitivity": sensitivity, "sessions_per_user": sessions}
            for legit, impostor in plan["splits"]
            for sensitivity in plan["sensitivities"] if only is None or sensitivity == only
            for sessions in plan["sessions"]]


def set_values(text: str, overrides: dict) -> str:
    """Replace each `key: value` line of the config text, keeping its comment."""
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


def run_one(name: str, overrides: dict, original: str, timeout: int) -> tuple[str, str]:
    """Write the run's own config snapshot, execute the notebook on it, return (status, error)."""
    folder = cfg_mod.RUNS / name
    if (folder / "config.yaml").exists():  # an earlier attempt that did not finish: start it fresh
        (folder / "config.yaml").write_text(set_values(original, overrides))
    else:
        cfg_mod.create_run(folder, set_values(original, overrides))
    try:
        result = subprocess.run([sys.executable, str(ROOT / "src" / "08_run_notebook.py"), "--run", name,
                                 "--timeout", str(timeout)],
                                cwd=ROOT.parent, capture_output=True, text=True)
    except OSError as error:
        return "failed", str(error)
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        return "failed", lines[-1] if lines else f"exit code {result.returncode}"
    return "ok", ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=ROOT / "batch.yaml", help="batch plan file")
    parser.add_argument("--only", type=float, help="run a single sensitivity, e.g. 0.2 (quick test)")
    parser.add_argument("--dry-run", action="store_true", help="list the runs and whether each is done, run nothing")
    parser.add_argument("--timeout", type=int, default=3600, help="seconds allowed per notebook run")
    parser.add_argument("--no-plot", action="store_true", help="skip the accuracy plots (16_plot_accuracy.py) at the end")
    args = parser.parse_args()

    runs = plan_runs(yaml.safe_load(args.plan.read_text()), args.only)
    original = CONFIG.read_text()
    set_values(original, runs[0] if runs else {})  # fail early if config.yaml lacks a key
    counts = {"ok": 0, "skipped": 0, "failed": 0}
    new_folders = []
    groups = set()
    try:
        for i, overrides in enumerate(runs, 1):
            name = cfg_mod.run_folder_name(cfg_mod.load_config(**overrides))
            folder = cfg_mod.RUNS / name
            prefix = f"[{i}/{len(runs)}] {name}"
            groups.add(name.split("/")[0])
            if (folder / DONE_MARKER).exists():
                counts["skipped"] += 1
                print(f"{prefix} ... done already, skipped")
                continue
            if args.dry_run:
                print(f"{prefix} ... to run")
                continue
            print(f"{prefix} ...", end=" ", flush=True)
            start = time.monotonic()
            status, error = run_one(name, overrides, original, args.timeout)
            seconds = round(time.monotonic() - start)
            counts[status] += 1
            if status == "ok":
                new_folders.append(name)
            print(f"{status} ({seconds // 60}m {seconds % 60:02d}s){'  ' + error if error else ''}")
            log_row({"time": datetime.now().isoformat(timespec="seconds"), "run": name,
                     "status": status, "seconds": seconds, "error": error})
    except KeyboardInterrupt:
        print("\nStopped. Run the same command again to continue; finished runs are skipped.")
        return

    to_run = len(runs) - counts["skipped"]
    if args.dry_run:
        print(f"\nDry run: {len(runs)} runs, {counts['skipped']} done, {to_run} to run.")
        return
    print(f"\nBatch: {counts['ok']} ok, {counts['skipped']} skipped, {counts['failed']} failed "
          f"of {len(runs)}. Log: {LOG}")
    if counts["failed"]:
        print("Failed runs are listed in the log; rerun the same command to retry only those.")
    if new_folders:
        print("\nTo share the new runs (runs/ is git-ignored, so -f is needed):")
        print("  git add -f " + " ".join(f"experiment_earl/runs/{name}" for name in new_folders))
    if not args.no_plot and counts["ok"] + counts["skipped"]:
        plot_groups(sorted(groups))


def plot_groups(groups: list[str]) -> None:
    """Run 16_plot_accuracy.py on each hash folder the plan used."""
    for group in groups:
        print(f"\nPlotting runs/{group} (16_plot_accuracy.py) ...", flush=True)
        result = subprocess.run([sys.executable, str(ROOT / "src" / "16_plot_accuracy.py"), group], cwd=ROOT.parent)
        if result.returncode != 0:
            print(f"Plotting runs/{group} failed (exit code {result.returncode}); rerun: "
                  f".venv/bin/python experiment_earl/src/16_plot_accuracy.py {group}")
        else:
            summarize_group(cfg_mod.RUNS / group)


def summarize_group(group: Path) -> None:
    """One row per run from accuracy.csv, written as summary/summary.csv and an overview summary/README.md."""
    table = pd.read_csv(group / "accuracy.csv")
    rows = []
    for (run, n_legit, n_impostor, sens, sessions), part in table.groupby(
            ["run", "n_legitimate", "n_impostor", "sensitivity", "sessions"]):
        legit, impostor = part[part.kind == "legitimate"], part[part.kind == "impostor"]
        rows.append({"split": f"{n_legit}_{n_impostor}", "n_legitimate": n_legit, "n_impostor": n_impostor,
                     "sensitivity": sens, "sessions": sessions, "run": run,
                     "legit_passed": int(legit.passed.sum()), "legit_tested": int(legit.tested.sum()),
                     "legit_accepted": f"{int(legit.through.sum())}/{len(legit)}",
                     "impostor_passed": int(impostor.passed.sum()), "impostor_tested": int(impostor.tested.sum()),
                     "impostors_through": f"{int(impostor.through.sum())}/{len(impostor)}"})
    summary = pd.DataFrame(rows).sort_values(["n_legitimate", "sensitivity", "sessions"])
    out = group / "summary"
    out.mkdir(exist_ok=True)
    summary.to_csv(out / "summary.csv", index=False)

    lines = [f"# Results of runs/{group.name}", "",
             f"Updated {datetime.now():%Y-%m-%d %H:%M} by `17_batch.py`. Settings shared by every run: "
             f"[`{summary.run.iloc[0]}/config.yaml`](../{summary.run.iloc[0]}/config.yaml).", "",
             "## Results per run", "",
             "Legitimate = own tested sessions that pass their own profile (higher is better). "
             "Impostor = impostor sessions that pass the profile (lower is better).", "",
             "| Split (legit_impostor) | Sensitivity | Sessions | Legitimate passed | Legitimate accepted | Impostor passed | Impostors through | Run folder |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    lines += [f"| {r.split} | {r.sensitivity:.2f} | {r.sessions} | {r.legit_passed}/{r.legit_tested} | {r.legit_accepted} | "
              f"{r.impostor_passed}/{r.impostor_tested} | {r.impostors_through} | [{r.run}](../{r.run}/) |"
              for r in summary.itertuples()]
    lines += ["", "## Plots (one per split and sensitivity)", ""]
    for split, part in summary.groupby("split", sort=False):
        lines.append(f"- {split}: " + ", ".join(f"[{s:.2f}](../accuracy_{split}_sensitivity_{s:.2f}.png)"
                                                 for s in sorted(part.sensitivity.unique())))
    lines += ["", "## Files", "",
              "- `summary/summary.csv`: the table above",
              "- `accuracy.csv`: every run and user (from `16_plot_accuracy.py`)",
              "- `accuracy_<legit>_<impostor>_sensitivity_<value>.png`: the plots",
              "- `<n_legitimate>_<n_impostor>_<sensitivity>_<sessions>/`: one folder per run (results/, figures/, notebooks/)",
              "- `../batch_log.csv`: which runs finished or failed, and how long each took", ""]
    (out / "README.md").write_text("\n".join(lines))
    print(f"Summary: {out / 'summary.csv'}, {out / 'README.md'}")


if __name__ == "__main__":
    main()
