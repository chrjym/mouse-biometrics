#!/usr/bin/env python3
"""New-seed check: the settings 12 (sensitivity matching) and 13 (raw, cohort) choose on the hash folder's seed, applied unchanged to new seeds; saved to runs/<hash>/seed_check/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
accuracy_mod = import_module("10_plot_accuracy")
cohort_mod = import_module("13_cohort_score")

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ["n_legitimate", "n_impostor"]
METHODS = ("match", "raw", "cohort")
LABELS = {"match": "12: sensitivity matching", "raw": "13: raw distance", "cohort": "13: cohort"}


def choose_cohort(cells: pd.DataFrame) -> pd.DataFrame:
    """13's choice per split and method on the training seed: sessions and threshold with the best user accuracy
    (ties: session accuracy, then fewer sessions)."""
    ranked = cells.sort_values(SPLIT + ["method", "user_accuracy", "session_accuracy", "sessions"],
                               ascending=[True, True, True, False, False, True])
    return ranked.groupby(SPLIT + ["method"], as_index=False).head(1).reset_index(drop=True)


def test_cohort(chosen: pd.DataFrame, sessions: pd.DataFrame, users: list[str], ratio: float) -> list[dict]:
    """The chosen sessions and threshold on another seed's claims: users through, accuracies and EER."""
    rows = []
    for row in chosen.itertuples():
        legit, impostor = users[:row.n_legitimate], users[row.n_legitimate:row.n_legitimate + row.n_impostor]
        part = cohort_mod.split_claims(sessions[sessions.sessions == row.sessions], legit, impostor)
        scores = cohort_mod.at_threshold(part, legit, row.method, ratio, row.threshold)
        rows.append({"n_legitimate": row.n_legitimate, "n_impostor": row.n_impostor, "method": row.method,
                     "sessions": row.sessions, "setting": f"{row.sessions} sessions, threshold {row.threshold:.3g}",
                     **{k: scores[k] for k in ("legit_through", "legit_users", "impostor_through", "impostor_users",
                                               "user_accuracy", "session_accuracy")},
                     "eer": cohort_mod.eer(part[part.genuine][row.method].to_numpy(),
                                           part[~part.genuine][row.method].to_numpy())})
    return rows


def test_match(chosen: pd.DataFrame, config: dict, seed: int) -> list[dict]:
    """12's chosen sensitivity and sessions per split, scored with 10's rules on another seed's draw."""
    rows = []
    for row in chosen.itertuples():
        run = {**config, "seed": seed, "n_legitimate": row.n_legitimate, "n_impostor": row.n_impostor,
               "sensitivity": row.sensitivity, "sessions_per_user": int(row.sessions)}
        users = pd.DataFrame(accuracy_mod.score_config(run, f"seed{seed}"))
        legit, impostor = users[users.kind == "legitimate"], users[users.kind == "impostor"]
        legit_share = legit.passed.sum() / legit.tested.sum()
        impostor_share = impostor.passed.sum() / impostor.tested.sum()
        rows.append({"n_legitimate": row.n_legitimate, "n_impostor": row.n_impostor, "method": "match",
                     "sessions": row.sessions, "setting": f"{row.sessions} sessions, sensitivity {row.sensitivity:g}",
                     "legit_through": int(legit.through.sum()), "legit_users": len(legit),
                     "impostor_through": int(impostor.through.sum()), "impostor_users": len(impostor),
                     "user_accuracy": (legit.through.mean() + 1 - impostor.through.mean()) / 2,
                     "session_accuracy": (legit_share + 1 - impostor_share) / 2, "eer": np.nan})
    return rows


def summarize(results: pd.DataFrame) -> pd.DataFrame:
    """Per split and method: the training seed's value next to the mean, lowest and highest over the test seeds."""
    train = results[results.role == "train"].set_index(SPLIT + ["method"])
    test = results[results.role == "test"].groupby(SPLIT + ["method"])
    summary = pd.DataFrame({
        "setting": train["setting"],
        "train_user_accuracy": train["user_accuracy"],
        "test_user_accuracy": test["user_accuracy"].mean(),
        "test_user_accuracy_min": test["user_accuracy"].min(),
        "test_user_accuracy_max": test["user_accuracy"].max(),
        "train_impostor_through": train["impostor_through"].astype(str) + "/" + train["impostor_users"].astype(str),
        "test_impostor_through": test["impostor_through"].sum().astype(str) + "/" + test["impostor_users"].sum().astype(str),
        "test_legit_through": test["legit_through"].sum().astype(str) + "/" + test["legit_users"].sum().astype(str),
        "train_eer": train["eer"],
        "test_eer": test["eer"].mean(),
    })
    return summary.reset_index()


def plot(results: pd.DataFrame, summary: pd.DataFrame, path: Path, title: str) -> None:
    """One panel per method: training-seed user accuracy (light bar), mean over the test seeds (dark bar) and each
    test seed (dots), per split."""
    methods = [m for m in METHODS if m in set(summary.method)]
    fig, axes = plt.subplots(1, len(methods), figsize=(5.2 * len(methods), 4.6), sharey=True, layout="constrained",
                             squeeze=False)
    splits = list(summary[SPLIT].drop_duplicates().itertuples(index=False, name=None))
    x = np.arange(len(splits))
    for ax, method in zip(axes[0], methods):
        part = summary[summary.method == method].set_index(SPLIT).reindex(splits)
        ax.bar(x - 0.2, part.train_user_accuracy, 0.38, color="#c9d6e3", label="chosen on the training seed")
        ax.bar(x + 0.2, part.test_user_accuracy, 0.38, color="#1f5f8b", label="new seeds (mean)")
        tests = results[(results.role == "test") & (results.method == method)]
        for i, split in enumerate(splits):
            values = tests[(tests.n_legitimate == split[0]) & (tests.n_impostor == split[1])].user_accuracy
            ax.scatter(np.full(len(values), i + 0.2), values, s=14, color="black", zorder=3,
                       label="each new seed" if i == 0 else None)
        ax.axhline(0.5, color="grey", linewidth=1, linestyle=":")
        ax.set_xticks(x, [f"{a}–{b}" for a, b in splits], fontsize=8)
        ax.set(title=LABELS[method], xlabel="split (legitimate–impostors)", ylim=(0, 1.05))
        ax.grid(alpha=0.3, axis="y")
    axes[0][0].set_ylabel("user accuracy (0.5 = chance)")
    axes[0][-1].legend(fontsize=8, loc="upper right")
    fig.suptitle(title, fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ (default: the one config.yaml selects)")
    parser.add_argument("--test-seeds", type=int, nargs="+", help="new seeds to test on (default: seed + 1 ... seed + 3)")
    parser.add_argument("--max-sessions", type=int, default=10, help="as in 13: highest sessions per user to choose from")
    parser.add_argument("--strokes-per-session", type=int, default=40, help="as in 13: library strokes per session")
    parser.add_argument("--cap", type=float, default=0.5, help="as in 13: DTW cost per point treated as equally far")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    folders = sorted(p.parent for p in group.glob("*/config.yaml"))
    baseline_path = group / "best" / "best.csv"
    if not folders or not baseline_path.exists():
        raise SystemExit(f"Needs run folders and {baseline_path}: run 10 and 12 on {group.name} first")
    config = cfg_mod.load_config(folders[0] / "config.yaml")
    runs = [cfg_mod.load_config(f / "config.yaml") for f in folders]
    splits = sorted({(c["n_legitimate"], c["n_impostor"]) for c in runs})
    k_values = sorted({c["sessions_per_user"] for c in runs if c["sessions_per_user"] <= args.max_sessions})
    seeds = args.test_seeds or [config["seed"] + i for i in (1, 2, 3)]
    ratio = config["match_session_ratio"]
    score = lambda users, order, ks: cohort_mod.score_sessions(users, order, ks, args.strokes_per_session, config,
                                                               args.cap, reserve=max(k_values))

    cohort_mod.load_nearest()
    match_mod.load_cache()
    print(f"Training seed {config['seed']}:", flush=True)
    users, order = cohort_mod.draw_all(config, config["seed"])
    train = score(users, order, k_values)
    cells = cohort_mod.score_cells(train, users, splits, ratio)
    chosen = choose_cohort(cells)
    baseline = pd.read_csv(baseline_path)
    rows = [{**r, "seed": config["seed"], "role": "train"} for r in test_match(baseline, config, config["seed"])]
    rows += [{**r, "seed": config["seed"], "role": "train"}
             for r in test_cohort(chosen, train, users, ratio)]
    for seed in seeds:
        print(f"Test seed {seed}:", flush=True)
        users, order = cohort_mod.draw_all(config, seed)
        sessions = score(users, order, sorted(set(chosen.sessions.astype(int))))
        rows += [{**r, "seed": seed, "role": "test"} for r in test_cohort(chosen, sessions, users, ratio)]
        rows += [{**r, "seed": seed, "role": "test"} for r in test_match(baseline, config, seed)]
        cohort_mod.save_nearest()
        match_mod.save_cache()

    results = pd.DataFrame(rows)
    summary = summarize(results)
    out = group / "seed_check"
    out.mkdir(exist_ok=True)
    results.to_csv(out / "results.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    plot(results, summary, out / "seed_check.png",
         f"runs/{group.name}: settings chosen on seed {config['seed']}, tested unchanged on seeds "
         f"{', '.join(map(str, seeds))} (new users order and sessions)")

    show = summary.pivot_table(index=SPLIT, columns="method", values=["train_user_accuracy", "test_user_accuracy"])
    print(show.round(2).to_string())
    print(summary.groupby("method")[["train_user_accuracy", "test_user_accuracy", "train_eer", "test_eer"]]
          .mean().round(3).to_string())
    print(f"Seeds: train {config['seed']}, test {seeds}")
    print(f"Output: {out}/ (results.csv, summary.csv, seed_check.png)")


if __name__ == "__main__":
    main()
