#!/usr/bin/env python3
"""Best sensitivity and sessions per split of each runs/<hash>/accuracy.csv (one hash per seed), where more legitimate than impostor sessions go through and at least --min-legit of legitimate sessions do, then highest balanced accuracy (ties: more sessions, higher sensitivity), plus a summary over all seeds."""

import argparse
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ["n_legitimate", "n_impostor"]
CELL = SPLIT + ["sensitivity", "sessions"]
SHOWN = SPLIT + ["sensitivity", "sessions", "legit_passed", "legit_tested", "impostor_passed", "impostor_tested",
                 "legit_accept_rate", "impostor_accept_rate", "balanced_accuracy", "qualifies"]


def score_cells(table: pd.DataFrame) -> pd.DataFrame:
    """Per (split, sensitivity, sessions): session counts of each kind, legitimate acceptance (TAR), impostor
    rejection (TRR), balanced accuracy = (TAR + TRR) / 2 (0.5 = chance) and gap = |TAR - TRR|; the same at user level."""
    sums = (table.groupby(CELL + ["kind"])
            .agg(passed=("passed", "sum"), tested=("tested", "sum"), through=("through", "sum"), users=("user", "size"))
            .unstack("kind"))
    cells = pd.DataFrame({
        "legit_passed": sums["passed"]["legitimate"], "legit_tested": sums["tested"]["legitimate"],
        "impostor_passed": sums["passed"]["impostor"], "impostor_tested": sums["tested"]["impostor"],
        "legit_users_through": sums["through"]["legitimate"], "legit_users": sums["users"]["legitimate"],
        "impostor_users_through": sums["through"]["impostor"], "impostor_users": sums["users"]["impostor"],
    })
    cells["legit_accept_rate"] = cells["legit_passed"] / cells["legit_tested"]
    cells["impostor_accept_rate"] = cells["impostor_passed"] / cells["impostor_tested"]
    cells["impostor_reject_rate"] = 1 - cells["impostor_accept_rate"]
    cells["balanced_accuracy"] = (cells["legit_accept_rate"] + cells["impostor_reject_rate"]) / 2
    cells["gap"] = (cells["legit_accept_rate"] - cells["impostor_reject_rate"]).abs()
    cells["worst_side"] = cells[["legit_accept_rate", "impostor_reject_rate"]].min(axis=1)
    cells["user_balanced_accuracy"] = (cells["legit_users_through"] / cells["legit_users"]
                                       + 1 - cells["impostor_users_through"] / cells["impostor_users"]) / 2
    return cells.reset_index()


def rank(cells: pd.DataFrame, groups: list[str], min_legit: float) -> pd.DataFrame:
    """qualifies = more legitimate than impostor sessions go through (legit_accept_rate > impostor_accept_rate) and
    at least min_legit of the legitimate sessions go through. Qualifying cells come first; then higher balanced
    accuracy, more legitimate sessions through, more sessions, higher sensitivity. Adds rank (1 = best) per group;
    a rank-1 cell with qualifies = False means no cell of that group qualifies."""
    cells = cells.round({"balanced_accuracy": 12, "legit_accept_rate": 12, "impostor_accept_rate": 12,
                         "worst_side": 12, "user_balanced_accuracy": 12})
    cells["legit_ahead"] = cells["legit_accept_rate"] > cells["impostor_accept_rate"]
    cells["legit_enough"] = cells["legit_accept_rate"] >= min_legit
    cells["qualifies"] = cells["legit_ahead"] & cells["legit_enough"]
    cells["beats_chance"] = cells["worst_side"] > 0.5
    keys = ["qualifies", "balanced_accuracy", "legit_accept_rate", "sessions", "sensitivity"]
    ranked = cells.sort_values(groups + keys, ascending=[True] * len(groups) + [False] * len(keys))
    ranked["rank"] = ranked.groupby(groups).cumcount() + 1 if groups else range(1, len(ranked) + 1)
    return ranked.reset_index(drop=True)


def pooled(table: pd.DataFrame) -> pd.DataFrame:
    """All splits added together per (sensitivity, sessions)."""
    merged = table.assign(n_legitimate="all", n_impostor="all")
    return score_cells(merged)


def seed_of(group: Path) -> int | None:
    """Seed from any config.yaml snapshot in the hash folder."""
    for snapshot in [*group.glob("*/config.yaml"), *group.glob("config.yaml")]:
        seed = (yaml.safe_load(snapshot.read_text()) or {}).get("seed")
        if seed is not None:
            return int(seed)
    return None


def process(group: Path, quiet: bool, min_legit: float) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Writes runs/<hash>/best_balanced/; returns (best rows, every scored cell) tagged with hash and seed."""
    source = group / "accuracy.csv"
    if not source.exists():
        print(f"skip {group.name}: no accuracy.csv")
        return None
    table = pd.read_csv(source)
    cells = rank(score_cells(table), SPLIT, min_legit)
    overall = rank(pooled(table), [], min_legit)
    best = pd.concat([cells[cells["rank"] == 1], overall[overall["rank"] == 1]], ignore_index=True)
    out = group / "best_balanced"
    out.mkdir(exist_ok=True)
    cells.to_csv(out / "scores.csv", index=False)
    overall.to_csv(out / "scores_all_splits.csv", index=False)
    best.to_csv(out / "best.csv", index=False)
    tag = {"hash": group.name, "seed": seed_of(group)}
    if not quiet:
        print(f"== {group.name} (seed {tag['seed']})")
        print(best[SHOWN].round(3).to_string(index=False))
    return best.assign(**tag), pd.concat([cells, overall], ignore_index=True).assign(**tag)


def summarize(cells: pd.DataFrame, bests: pd.DataFrame, min_legit: float) -> pd.DataFrame:
    """Per (split, sensitivity, sessions) over seeds: mean/std/min of each score, seeds, seeds where it is the best
    cell and where both rates beat 0.5; ranked like rank() on the means (best first within each split)."""
    summary = (cells.groupby(CELL)
               .agg(seeds=("seed", "size"),
                    worst_side=("worst_side", "mean"), worst_side_std=("worst_side", "std"),
                    worst_side_min=("worst_side", "min"),
                    balanced_accuracy=("balanced_accuracy", "mean"), balanced_accuracy_std=("balanced_accuracy", "std"),
                    legit_accept_rate=("legit_accept_rate", "mean"), impostor_accept_rate=("impostor_accept_rate", "mean"),
                    impostor_reject_rate=("impostor_reject_rate", "mean"),
                    user_balanced_accuracy=("user_balanced_accuracy", "mean"),
                    seeds_qualifying=("qualifies", "sum"), seeds_beating_chance=("beats_chance", "sum"))
               .reset_index())
    wins = bests.groupby(CELL).size().rename("times_best").reset_index()
    summary = summary.merge(wins, on=CELL, how="left").fillna({"times_best": 0})
    summary["times_best"] = summary["times_best"].astype(int)
    return rank(summary, SPLIT, min_legit)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hashes", nargs="*", help="folders under runs/ holding accuracy.csv "
                                                  "(default: the one config.yaml selects)")
    parser.add_argument("--all", action="store_true", help="every runs/<hash>/ that has accuracy.csv")
    parser.add_argument("--min-legit", type=float, default=0.5,
                        help="share of legitimate sessions that must go through for a setting to qualify (default 0.5)")
    args = parser.parse_args()
    if args.all:
        groups = sorted(p.parent for p in cfg_mod.RUNS.glob("*/accuracy.csv"))
    else:
        names = args.hashes or [cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0]]
        groups = [cfg_mod.RUNS / n for n in names]

    quiet = len(groups) > 5
    results = [r for r in (process(g, quiet, args.min_legit) for g in groups) if r is not None]
    if not results:
        raise SystemExit("No accuracy.csv found: run section 4 of the notebook (or 10_plot_accuracy.py) first")
    print(f"Per hash ({len(results)}): best_balanced/ (best.csv, scores.csv, scores_all_splits.csv)")
    if len(results) > 1:
        bests = pd.concat([b for b, _ in results], ignore_index=True)
        cells = pd.concat([c for _, c in results], ignore_index=True)
        summary = summarize(cells, bests, args.min_legit)
        bests.to_csv(cfg_mod.RUNS / "best_balanced_seeds.csv", index=False)
        summary.to_csv(cfg_mod.RUNS / "best_balanced_summary.csv", index=False)
        top = summary[summary["rank"] == 1]
        print(f"\nBest per split over {bests['seed'].nunique()} seeds (means):")
        print(top[SPLIT + ["sensitivity", "sessions", "seeds", "worst_side", "worst_side_std", "balanced_accuracy",
                           "legit_accept_rate", "impostor_accept_rate", "times_best", "seeds_qualifying", "qualifies"]]
              .round(3).to_string(index=False))
        print(f"Output: {cfg_mod.RUNS / 'best_balanced_seeds.csv'} (each seed's best), "
              f"{cfg_mod.RUNS / 'best_balanced_summary.csv'} (every cell over seeds)")


if __name__ == "__main__":
    main()
