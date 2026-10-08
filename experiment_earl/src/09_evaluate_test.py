#!/usr/bin/env python3
"""Enroll each user on training sessions, verify their labeled test sessions, and report FAR, FRR and EER."""

import argparse
import csv
import json
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")


def load_labels(config: dict) -> dict[str, list[tuple[str, int]]]:
    """Labeled test sessions per user folder as (session name, is_illegal)."""
    with (cfg_mod.ROOT / config["labels_file"]).open(newline="") as handle:
        labels = {row["filename"]: int(row["is_illegal"]) for row in csv.DictReader(handle)}
    test_dir = cfg_mod.ROOT / config["test_dir"]
    return {
        user.name: [(s.name, labels[s.name]) for s in sorted(user.iterdir()) if s.name in labels]
        for user in sorted(test_dir.iterdir()) if user.is_dir()
    }


def enrollment(config: dict, user: str) -> list[str]:
    names = [p.name for p in cfg_mod.list_sessions(config, user)]
    k = config["test_enroll_sessions"]
    return names if not k or k >= len(names) else sorted(random.Random(f"{config['seed']}-{user}").sample(names, k))


def far_frr(genuine: np.ndarray, impostor: np.ndarray, threshold: float) -> tuple[float, float]:
    """A session is accepted when its score is at least `threshold`."""
    far = float(np.mean(impostor >= threshold)) if len(impostor) else np.nan
    frr = float(np.mean(genuine < threshold)) if len(genuine) else np.nan
    return far, frr


def equal_error_rate(genuine: np.ndarray, impostor: np.ndarray) -> tuple[float, float]:
    """EER and the score threshold where FAR and FRR are closest."""
    if not len(genuine) or not len(impostor):
        return np.nan, np.nan
    thresholds = np.unique(np.concatenate([genuine, impostor, [np.inf]]))
    rates = np.array([far_frr(genuine, impostor, t) for t in thresholds])
    i = int(np.argmin(np.abs(rates[:, 0] - rates[:, 1])))
    return float(rates[i].mean()), float(thresholds[i])


def summarize(scores: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for tol, by_tol in scores.groupby("tolerance"):
        groups = [(user, g) for user, g in by_tol.groupby("user")] + [("all users", by_tol)]
        for user, g in groups:
            genuine = g.loc[g["is_illegal"] == 0, "score"].to_numpy()
            impostor = g.loc[g["is_illegal"] == 1, "score"].to_numpy()
            far, frr = far_frr(genuine, impostor, config["match_shape_ratio"])
            eer, eer_at = equal_error_rate(genuine, impostor)
            rows.append({
                "tolerance": tol, "user": user, "n_genuine": len(genuine), "n_impostor": len(impostor),
                "genuine_mean_score": genuine.mean() if len(genuine) else np.nan,
                "impostor_mean_score": impostor.mean() if len(impostor) else np.nan,
                "far": far, "frr": frr, "eer": eer, "eer_threshold": eer_at,
            })
    return pd.DataFrame(rows).round(4)


def plot(scores: pd.DataFrame, summary: pd.DataFrame, config: dict, figures) -> None:
    tolerances = sorted(scores["tolerance"].unique())
    grid = np.linspace(0, 1, 201)

    fig, axes = plt.subplots(1, len(tolerances), figsize=(4.5 * len(tolerances), 4), squeeze=False)
    for ax, tol in zip(axes[0], tolerances):
        g = scores[scores["tolerance"] == tol]
        genuine = g.loc[g["is_illegal"] == 0, "score"].to_numpy()
        impostor = g.loc[g["is_illegal"] == 1, "score"].to_numpy()
        rates = np.array([far_frr(genuine, impostor, t) for t in grid])
        pooled = summary[(summary["tolerance"] == tol) & (summary["user"] == "all users")].iloc[0]
        ax.plot(grid, rates[:, 0], label="FAR (impostor accepted)", color="tab:red")
        ax.plot(grid, rates[:, 1], label="FRR (genuine rejected)", color="tab:blue")
        ax.axvline(config["match_shape_ratio"], color="gray", linestyle=":", label="match_shape_ratio")
        ax.plot(pooled["eer_threshold"], pooled["eer"], "ko")
        ax.annotate(f"EER {pooled['eer']:.1%}", (pooled["eer_threshold"], pooled["eer"]),
                    textcoords="offset points", xytext=(8, 8), fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("score threshold (share of chunks that match)")
        ax.set_title(f"dtw_tolerance {tol}")
    axes[0][0].set_ylabel("error rate")
    axes[0][0].legend(fontsize=7, loc="center right")
    fig.suptitle("Test set: FAR and FRR, all users pooled")
    fig.tight_layout()
    fig.savefig(figures / "test_far_frr.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(tolerances), figsize=(4.5 * len(tolerances), 4), squeeze=False)
    bins = np.linspace(0, 1, 26)
    for ax, tol in zip(axes[0], tolerances):
        g = scores[scores["tolerance"] == tol]
        ax.hist(g.loc[g["is_illegal"] == 0, "score"], bins=bins, alpha=0.6, label="genuine", color="tab:blue")
        ax.hist(g.loc[g["is_illegal"] == 1, "score"], bins=bins, alpha=0.6, label="impostor", color="tab:red")
        ax.set_xlabel("score (share of chunks that match)")
        ax.set_title(f"dtw_tolerance {tol}")
    axes[0][0].set_ylabel("test sessions")
    axes[0][0].legend(fontsize=8)
    fig.suptitle("Test set: score of genuine vs impostor sessions (they should separate)")
    fig.tight_layout()
    fig.savefig(figures / "test_scores.png", dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    out = run / "results" / "test_eval"
    out.mkdir(parents=True, exist_ok=True)
    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    match_mod.load_cache()

    labels = load_labels(config)
    users = [u for u in labels if not args.user or u in args.user]
    rows = []
    for tol in config["test_tolerances"]:
        settings = {**config, "dtw_tolerance": tol}
        for user in users:
            profile = [match_mod.dataset_session(user, n, settings) for n in enrollment(config, user)]
            for name, is_illegal in labels[user]:
                session = match_mod.dataset_session(user, name, settings, folder=config["test_dir"])
                matched = match_mod.matched_chunks(session, profile, settings)
                rows.append({"tolerance": tol, "user": user, "session": name, "is_illegal": is_illegal,
                             "n_chunks": session.n_chunks, "score": matched / max(session.n_chunks, 1)})
            match_mod.save_cache()
            print(f"tolerance {tol} {user}: {len(labels[user])} labeled test sessions scored", flush=True)

    scores = pd.DataFrame(rows)
    scores.to_csv(out / "scores.csv", index=False)
    summary = summarize(scores, config)
    summary.to_csv(out / "summary.csv", index=False)
    plot(scores, summary, config, figures)
    (out / "settings.json").write_text(json.dumps(
        {"users": users, "enrolled": {u: enrollment(config, u) for u in users}, "config": config}, indent=2) + "\n")

    pooled = summary[summary["user"] == "all users"]
    print(f"\nAll users pooled (accept when score >= match_shape_ratio {config['match_shape_ratio']}):")
    for _, row in pooled.iterrows():
        print(f"  tolerance {row['tolerance']}: genuine score {row['genuine_mean_score']:.3f}, "
              f"impostor score {row['impostor_mean_score']:.3f} | FAR {row['far']:.1%}  FRR {row['frr']:.1%}  "
              f"EER {row['eer']:.1%}")
    print(f"Output: {out}, {figures / 'test_far_frr.png'}, {figures / 'test_scores.png'}")


if __name__ == "__main__":
    main()
