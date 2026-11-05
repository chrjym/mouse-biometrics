#!/usr/bin/env python3
"""Best sensitivity (experiment 1) and sessions (experiment 2) from each runs/<hash>/experiments/ (one hash per seed): more legitimate than impostor sessions must go through, then highest accuracy, ties to higher sensitivity / more sessions; plus a summary over all seeds."""

import argparse
import shutil
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ["TP", "FP", "FN", "TN"]   # positive = impostor: TP rejected, FN let in, TN legitimate accepted, FP blocked
X = {"exp1": "sensitivity", "exp2": "sessions"}
SHOWN = ["split", "sensitivity", "sessions", "TP", "FP", "FN", "TN", "legit_through", "impostor_through", "accuracy",
         "qualifies", "notebook_best"]


def score(points: pd.DataFrame, x: str) -> pd.DataFrame:
    """Per split and point (the point's own counts, not the running totals), plus split 'all' = every split added
    (= the notebook's <exp>_overall.csv): legit_through = TN / (TN + FP), impostor_through = FN / (FN + TP),
    accuracy = (TP + TN) / all as in the notebook, balanced_accuracy = (legit_through + impostor rejected) / 2."""
    keys = ["sensitivity", "sessions"]
    per_split = points.groupby(["split"] + keys, as_index=False, sort=False)[COUNTS].sum()
    pooled = points.groupby(keys, as_index=False)[COUNTS].sum().assign(split="all")
    cells = pd.concat([per_split, pooled], ignore_index=True)
    cells["legit_through"] = cells["TN"] / (cells["TN"] + cells["FP"])
    cells["impostor_through"] = cells["FN"] / (cells["FN"] + cells["TP"])
    cells["accuracy"] = (cells["TP"] + cells["TN"]) / cells[COUNTS].sum(axis=1)
    cells["balanced_accuracy"] = (cells["legit_through"] + 1 - cells["impostor_through"]) / 2
    # the notebook's own pick: highest accuracy, ties to the lower x
    first = cells.round({"accuracy": 4}).sort_values(["split", "accuracy", x], ascending=[True, False, True])
    cells["notebook_best"] = cells.index.isin(first.groupby("split").head(1).index)
    return cells


def rank(cells: pd.DataFrame, x: str, min_legit: float) -> pd.DataFrame:
    """qualifies = more legitimate than impostor sessions go through (legit_through > impostor_through) and
    legit_through >= min_legit. Per split: qualifying first, then higher accuracy, higher legit_through, higher x.
    A rank-1 row with qualifies = False means nothing in that split qualifies."""
    cells = cells.round({"legit_through": 12, "impostor_through": 12, "accuracy": 12, "balanced_accuracy": 12})
    cells["qualifies"] = (cells["legit_through"] > cells["impostor_through"]) & (cells["legit_through"] >= min_legit)
    keys = ["qualifies", "accuracy", "legit_through", x]
    ranked = cells.sort_values(["split"] + keys, ascending=[True] + [False] * len(keys), kind="stable")
    ranked["rank"] = ranked.groupby("split").cumcount() + 1
    return ranked.reset_index(drop=True)


def seed_of(group: Path) -> int | None:
    """Seed from any config.yaml snapshot in the hash folder (run folders, sweep/)."""
    for snapshot in group.glob("*/config.yaml"):
        seed = (yaml.safe_load(snapshot.read_text()) or {}).get("seed")
        if seed is not None:
            return int(seed)
    return None


def process(group: Path, min_legit: float, quiet: bool) -> pd.DataFrame | None:
    """Writes runs/<hash>/best_balanced/; returns every ranked point of both experiments, tagged."""
    source = group / "experiments"
    if not (source / "exp1_points.csv").exists():
        print(f"skip {group.name}: no experiments/exp1_points.csv")
        return None
    tag = {"hash": group.name, "seed": seed_of(group)}
    out = group / "best_balanced"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir()
    ranked = []
    for exp, x in X.items():
        path = source / f"{exp}_points.csv"
        if not path.exists():
            continue
        cells = rank(score(pd.read_csv(path), x), x, min_legit).assign(experiment=exp, **tag)
        cells.to_csv(out / f"{exp}_scores.csv", index=False)
        ranked.append(cells)
    table = pd.concat(ranked, ignore_index=True)
    best = table[table["rank"] == 1]
    best.to_csv(out / "best.csv", index=False)
    if not quiet:
        print(f"== {group.name} (seed {tag['seed']})")
        for exp, rows in best.groupby("experiment"):
            print(f"{exp} (best {X[exp]}):")
            print(rows[SHOWN].round(3).to_string(index=False))
    return table


def summarize(table: pd.DataFrame) -> pd.DataFrame:
    """Per experiment, split and point over seeds: mean rates, seeds, times_best (rank 1 and qualifies),
    seeds_qualifying, how often it is the notebook's pick. Experiment 2 is grouped by sessions only (its sensitivity is each seed's experiment-1 best)."""
    parts = []
    for exp, x in X.items():
        part = table[table["experiment"] == exp]
        if part.empty:
            continue
        part = part.assign(won=(part["rank"] == 1) & part["qualifies"])
        stats = (part.groupby(["split", x])
                 .agg(seeds=("seed", "size"), accuracy=("accuracy", "mean"), accuracy_std=("accuracy", "std"),
                      legit_through=("legit_through", "mean"), impostor_through=("impostor_through", "mean"),
                      balanced_accuracy=("balanced_accuracy", "mean"),
                      times_best=("won", "sum"),
                      seeds_qualifying=("qualifies", "sum"), times_notebook_best=("notebook_best", "sum"))
                 .reset_index())
        stats = stats.sort_values(["split", "times_best", "seeds_qualifying", "accuracy", x],
                                  ascending=[True, False, False, False, False])
        parts.append(stats.assign(experiment=exp))
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hashes", nargs="*", help="folders under runs/ holding experiments/ "
                                                  "(default: the one config.yaml selects)")
    parser.add_argument("--all", action="store_true", help="every runs/<hash>/ that has experiments/ (e.g. 500 seeds)")
    parser.add_argument("--min-legit", type=float, default=0.5,
                        help="share of legitimate sessions that must go through to qualify (default 0.5)")
    args = parser.parse_args()
    if args.all:
        groups = sorted(p.parent.parent for p in cfg_mod.RUNS.glob("*/experiments/exp1_points.csv"))
    else:
        names = args.hashes or [cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0]]
        groups = [cfg_mod.RUNS / n for n in names]

    quiet = len(groups) > 5
    tables = [t for t in (process(g, args.min_legit, quiet) for g in groups) if t is not None]
    if not tables:
        raise SystemExit("No experiments/ found: run section 9 of the notebook first")
    print(f"Per hash ({len(tables)}): best_balanced/ (best.csv, exp1_scores.csv, exp2_scores.csv)")
    if len(tables) > 1:
        table = pd.concat(tables, ignore_index=True)
        table[table["rank"] == 1].to_csv(cfg_mod.RUNS / "best_balanced_seeds.csv", index=False)
        summary = summarize(table)
        summary.to_csv(cfg_mod.RUNS / "best_balanced_summary.csv", index=False)
        print(f"\nMost often best over {table['seed'].nunique()} seeds:")
        top = summary.groupby(["experiment", "split"], sort=False).head(1)
        print(top[["experiment", "split", "sensitivity", "sessions", "seeds", "times_best", "seeds_qualifying",
                   "accuracy", "legit_through", "impostor_through"]].round(3).to_string(index=False))
        print(f"Output: {cfg_mod.RUNS / 'best_balanced_seeds.csv'} (each seed's best), "
              f"{cfg_mod.RUNS / 'best_balanced_summary.csv'} (every point over seeds)")


if __name__ == "__main__":
    main()
