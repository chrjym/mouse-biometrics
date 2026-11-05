#!/usr/bin/env python3
"""Rank every sensitivity (experiment 1) and session count (experiment 2) from best to worst over every seed's runs/<hash>/experiments/ into runs/best_balanced/<exp>_ranking.csv: more legitimate than impostor sessions must go through, then highest accuracy, ties to higher sensitivity / more sessions."""

import argparse
from importlib import import_module
from pathlib import Path

import pandas as pd
import yaml

cfg_mod = import_module("00_config")

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ["TP", "FP", "FN", "TN"]   # positive = impostor: TP rejected, FN let in, TN legitimate accepted, FP blocked
X = {"exp1": "sensitivity", "exp2": "sessions"}


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


def process(group: Path, min_legit: float) -> pd.DataFrame | None:
    """Every ranked point of both experiments of one hash folder (one seed), tagged with hash and seed."""
    source = group / "experiments"
    if not (source / "exp1_points.csv").exists():
        print(f"skip {group.name}: no experiments/exp1_points.csv")
        return None
    tag = {"hash": group.name, "seed": seed_of(group)}
    ranked = [rank(score(pd.read_csv(source / f"{exp}_points.csv"), x), x, min_legit).assign(experiment=exp, **tag)
              for exp, x in X.items() if (source / f"{exp}_points.csv").exists()]
    return pd.concat(ranked, ignore_index=True)


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
        stats["rank"] = stats.groupby("split").cumcount() + 1
        stats["qualifies"] = stats["seeds_qualifying"] > 0
        parts.append(stats.assign(experiment=exp))
    summary = pd.concat(parts, ignore_index=True)
    first = ["experiment", "split", "rank", "sensitivity", "sessions"]
    return summary[[c for c in first if c in summary] + [c for c in summary.columns if c not in first]]


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
        groups = sorted(p.parent.parent for p in cfg_mod.RUNS.glob("*/experiments/exp1_points.csv"))

    tables = [t for t in (process(g, args.min_legit) for g in groups) if t is not None]
    if not tables:
        raise SystemExit("No experiments/ found: run section 9 of the notebook first")
    table = pd.concat(tables, ignore_index=True)
    out = cfg_mod.RUNS / "best_balanced"
    if out.exists():
        for old in [*out.glob("*.csv"), *out.glob("by_split/*.csv")]:
            old.unlink()
    (out / "by_split").mkdir(parents=True, exist_ok=True)
    first = ["experiment", "seed", "hash", "split", "rank"]
    table = table[first + [c for c in table.columns if c not in first]]
    table.sort_values(["experiment", "seed", "split", "rank"]).to_csv(out / "scores.csv", index=False)
    table[table["rank"] == 1].sort_values(["experiment", "seed", "split"]).to_csv(out / "seeds.csv", index=False)
    summary = summarize(table)
    for (exp, split), ranking in summary.groupby(["experiment", "split"]):
        ranking = ranking.sort_values("rank").drop(columns=[c for c in ("sensitivity", "sessions") if c != X[exp]])
        path = out / f"{exp}_ranking.csv" if split == "all" else out / "by_split" / f"{exp}_{split.replace(' ', '')}_ranking.csv"
        ranking.to_csv(path, index=False)

    print(f"{table['seed'].nunique()} seeds ({len(tables)} hash folders), min legitimate through {args.min_legit:g}")
    for exp, x in X.items():
        ranking = summary[(summary["experiment"] == exp) & (summary["split"] == "all")].sort_values("rank")
        print(f"\n{exp}: top 5 {x} (all splits, ranked over seeds)")
        print(ranking.head(5)[["rank", x, "seeds", "times_best", "seeds_qualifying", "accuracy", "legit_through",
                               "impostor_through"]].round(3).to_string(index=False))
    print(f"\nOutput: {out}/ (exp1_ranking.csv, exp2_ranking.csv = rank 1 to last over all seeds, all splits; "
          f"by_split/ = the same per split; seeds.csv = each seed's best; scores.csv = every point of every seed)")

if __name__ == "__main__":
    main()
