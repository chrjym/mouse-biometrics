#!/usr/bin/env python3
"""One row per seed: the notebook's best sensitivity (experiment 1, exp1_overall.csv) and its accuracy, plus experiment 2's best sessions, from every runs/<hash>/experiments/; seeds ranked by accuracy, highest first, into runs/best_balanced/best_per_seed.csv."""

import argparse
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ["TP", "FP", "FN", "TN"]   # positive = impostor: TP rejected, FN let in, TN legitimate accepted, FP blocked


def best_point(path: Path, x: str, min_legit: float) -> pd.Series:
    """The notebook's single best point of one experiment: the `best = True` row of <exp>_overall.csv (all splits
    added; highest accuracy, ties to the lower x), the same as the exp1.png / exp2.png title. legit_ahead = more
    legitimate than impostor sessions through and legitimate through >= min_legit (a check, it does not change the
    pick)."""
    table = pd.read_csv(path)
    best = table[table["best"]].iloc[0].copy()
    best["legit_through"] = best["TN"] / (best["TN"] + best["FP"])
    best["impostor_through"] = best["FN"] / (best["FN"] + best["TP"])
    best["legit_ahead"] = bool(best["legit_through"] > best["impostor_through"] and best["legit_through"] >= min_legit)
    return best


def seed_of(group: Path) -> int | None:
    """Seed from any config.yaml snapshot in the hash folder (run folders, sweep/)."""
    for snapshot in group.glob("*/config.yaml"):
        seed = (yaml.safe_load(snapshot.read_text()) or {}).get("seed")
        if seed is not None:
            return int(seed)
    return None


def seed_row(group: Path, min_legit: float) -> dict | None:
    """The seed's best sensitivity (experiment 1) and best sessions (experiment 2, at that sensitivity)."""
    source = group / "experiments"
    if not (source / "exp1_overall.csv").exists():
        print(f"skip {group.name}: no experiments/exp1_overall.csv")
        return None
    e1 = best_point(source / "exp1_overall.csv", "sensitivity", min_legit)
    row = {"seed": seed_of(group), "hash": group.name, "sensitivity": e1["sensitivity"], "accuracy": e1["accuracy"],
           "legit_through": round(e1["legit_through"], 4), "impostor_through": round(e1["impostor_through"], 4),
           **{c: int(e1[c]) for c in COUNTS}, "legit_ahead": e1["legit_ahead"]}
    if (source / "exp2_overall.csv").exists():
        e2 = best_point(source / "exp2_overall.csv", "sessions", min_legit)
        row |= {"exp2_sessions": int(e2["sessions"]), "exp2_accuracy": e2["accuracy"],
                "exp2_legit_through": round(e2["legit_through"], 4),
                "exp2_impostor_through": round(e2["impostor_through"], 4), "exp2_legit_ahead": e2["legit_ahead"]}
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hashes", nargs="*", help="only these folders under runs/ (default: every runs/<hash>/ that "
                                                  "has experiments/, i.e. every seed)")
    parser.add_argument("--min-legit", type=float, default=0.5,
                        help="share of legitimate sessions that must go through to qualify (default 0.5)")
    args = parser.parse_args()
    if args.hashes:
        groups = [cfg_mod.RUNS / n for n in args.hashes]
    else:
        groups = sorted(p.parent.parent for p in cfg_mod.RUNS.glob("*/experiments/exp1_overall.csv"))

    rows = [r for r in (seed_row(g, args.min_legit) for g in groups) if r is not None]
    if not rows:
        raise SystemExit("No experiments/ found: run section 9 of the notebook first")
    table = (pd.DataFrame(rows)
             .sort_values(["accuracy", "sensitivity"], ascending=False, kind="stable")
             .reset_index(drop=True))
    table.insert(0, "rank", range(1, len(table) + 1))
    out = cfg_mod.RUNS / "best_balanced"
    out.mkdir(exist_ok=True)
    for old in [*out.glob("*.csv"), *out.glob("by_split/*.csv")]:
        old.unlink()
    if (out / "by_split").exists():
        (out / "by_split").rmdir()
    path = out / "best_per_seed.csv"
    table.to_csv(path, index=False)

    print(table[["rank", "seed", "hash", "sensitivity", "accuracy", "legit_through", "impostor_through", "legit_ahead",
                 "exp2_sessions", "exp2_accuracy"]].to_string(index=False))
    print(f"{len(table)} seeds, ranked by accuracy (ties: higher sensitivity); "
          f"{int(table['legit_ahead'].sum())} with more legitimate than impostor sessions through")
    print(f"Output: {path}")


if __name__ == "__main__":
    main()
