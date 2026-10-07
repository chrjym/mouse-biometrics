#!/usr/bin/env python3
"""Turn trial results into the threshold matched_detected / total_impostor_user and append to results/summary.csv."""

import argparse
import csv
import json
from importlib import import_module

cfg_mod = import_module("00_config")

COLUMNS = ["trial", "n_legit", "n_sessions", "n_impostor", "matched_detected", "threshold"]


def compute_threshold(records: list[dict], n_impostor: int) -> tuple[int, float]:
    detected = sum(record["matched"] for record in records)
    return detected, detected / n_impostor


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    results = cfg_mod.ROOT / "results"
    rows = {}
    for path in sorted(results.glob("trial_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        trial = json.loads(path.read_text())
        detected, threshold = compute_threshold(trial["records"], trial["n_impostor"])
        rows[trial["trial"]] = {
            "trial": trial["trial"], "n_legit": len(trial["legitimate"]),
            "n_sessions": trial["config"]["sessions_per_user"], "n_impostor": trial["n_impostor"],
            "matched_detected": detected, "threshold": round(threshold, 4),
        }
    with (results / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows.values())
    for row in rows.values():
        print(f"trial {row['trial']}: {row['matched_detected']}/{row['n_impostor']} impostors matched, "
              f"threshold {row['threshold']:.2f}")
    print(f"Output: {results / 'summary.csv'}")


if __name__ == "__main__":
    main()
