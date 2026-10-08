#!/usr/bin/env python3
"""Sweep sessions per user x legitimate users x impostor users and report where the threshold saturates or jumps."""

import argparse
import json
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")


def draw(config: dict, seed: int) -> tuple[list[str], dict[str, list[tuple[str, str]]]]:
    """A shuffled user list (legitimate users come from the front, impostors from the back, so
    both sets are nested and never overlap) and each user's shuffled session pool as (folder, name)."""
    users = cfg_mod.list_users(config)
    random.Random(seed).shuffle(users)
    return users, {user: cfg_mod.session_pool(config, user, seed) for user in users}


def pair_scores(config: dict, seed: int, sessions_max: int) -> tuple[list[dict], list[dict]]:
    """For every session count and every (impostor, legitimate) user pair: the share of the impostor's
    sessions that match the legitimate profile, and their mean chunk match ratio. Also, per legitimate
    user, the share of Balabit impostor attempts on them that their profile accepts."""
    users, order = draw(config, seed)
    rows, attempt_rows = [], []
    for k in range(1, sessions_max + 1):
        picked = {u: [match_mod.dataset_session(u, n, config, folder=f) for f, n in order[u][:k]] for u in users}
        for legit, ratios in match_mod.attempt_scores(picked, config).items():
            if ratios:
                attempt_rows.append({"seed": seed, "sessions": k, "legit": legit, "attempts": len(ratios),
                                     "accept_rate": float(np.mean([r >= config["match_shape_ratio"] for r in ratios]))})
        for impostor in users:
            for legit in users:
                if impostor == legit:
                    continue
                ratios = [match_mod.matched_chunks(s, picked[legit], config) / max(s.n_chunks, 1)
                          for s in picked[impostor]]
                rows.append({
                    "seed": seed, "sessions": k, "impostor": impostor, "legit": legit,
                    "session_share": float(np.mean([r >= config["match_shape_ratio"] for r in ratios])),
                    "mean_chunk_ratio": float(np.mean(ratios)),
                })
    return rows, attempt_rows


def cell_results(pairs: pd.DataFrame, attempts: pd.DataFrame, config: dict,
                 users_by_seed: dict[int, list[str]]) -> pd.DataFrame:
    """matched_detected and threshold for every (seed, sessions, n_legit, n_impostor) with n_legit + n_impostor <= users,
    plus the mean share of Balabit impostor attempts accepted by the cell's legitimate users (NaN without test files)."""
    share = pairs.set_index(["seed", "sessions", "impostor", "legit"])["session_share"]
    accept = attempts.set_index(["seed", "sessions", "legit"])["accept_rate"] if len(attempts) else pd.Series(dtype=float)
    rows = []
    for (seed, k), _ in pairs.groupby(["seed", "sessions"]):
        users = users_by_seed[seed]
        for n_legit in range(1, len(users)):
            legit = users[:n_legit]
            for n_impostor in range(1, len(users) - n_legit + 1):
                impostors = users[::-1][:n_impostor]
                matched = sum(
                    max(share[(seed, k, v, u)] for u in legit) >= config["match_session_ratio"] for v in impostors
                )
                rates = [accept[(seed, k, u)] for u in legit if (seed, k, u) in accept.index]
                rows.append({"seed": seed, "sessions": k, "n_legit": n_legit, "n_impostor": n_impostor,
                             "matched_detected": matched, "threshold": matched / n_impostor,
                             "attempt_accept_rate": float(np.mean(rates)) if rates else np.nan})
    return pd.DataFrame(rows)


def saturation(means: pd.Series, delta: float) -> tuple[int, int, float]:
    """First step after which every further change stays below `delta`, and the biggest single jump."""
    steps = means.index.to_list()
    diffs = means.diff().iloc[1:]
    flat_from = steps[-1]
    for i in range(len(steps) - 1, 0, -1):
        if abs(diffs.iloc[i - 1]) >= delta:
            break
        flat_from = steps[i - 1]
    jump_at = int(diffs.abs().idxmax()) if len(diffs) else steps[0]
    return flat_from, jump_at, float(diffs.abs().max()) if len(diffs) else 0.0


def plot_heatmaps(summary: pd.DataFrame, path, n_users: int) -> None:
    sessions = sorted(summary["sessions"].unique())
    levels = np.round(np.arange(0, 1.01, 0.1), 1)
    fig, axes = plt.subplots(1, len(sessions), figsize=(4.2 * len(sessions), 4.4), sharey=True)
    for ax, k in zip(np.atleast_1d(axes), sessions):
        grid = (summary[summary["sessions"] == k]
                .pivot(index="n_impostor", columns="n_legit", values="threshold_mean")
                .reindex(index=range(1, n_users), columns=range(1, n_users)))
        image = ax.imshow(grid.to_numpy(), cmap="YlOrRd", norm=BoundaryNorm(levels, 256), origin="lower")
        for (r, c), value in np.ndenumerate(grid.to_numpy()):
            if not np.isnan(value):
                ax.text(c, r, f"{value:.2f}", ha="center", va="center", fontsize=7)
        ax.set_xticks(range(n_users - 1), grid.columns)
        ax.set_yticks(range(n_users - 1), grid.index)
        ax.set_xlabel("legitimate users")
        ax.set_title(f"{k} session{'s' if k > 1 else ''} per user")
    np.atleast_1d(axes)[0].set_ylabel("impostor users")
    fig.colorbar(image, ax=axes, ticks=levels, label="mean threshold (0 = best)", shrink=0.8)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def plot_lines(summary: pd.DataFrame, path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for column, ax, label in (("sessions", axes[0], "sessions per user"),
                              ("n_legit", axes[1], "legitimate users"),
                              ("n_impostor", axes[2], "impostor users")):
        others = [c for c in ("sessions", "n_legit", "n_impostor") if c != column]
        # one line per value of the first other axis, averaged over the second
        curves = summary.groupby([others[0], column])["threshold_mean"].mean().unstack(0)
        curves.plot(ax=ax, marker="o")
        ax.set_xticks(curves.index)
        ax.set_xlabel(label)
        ax.set_ylabel("mean threshold")
        ax.set_ylim(0, 1)
        ax.legend(title=others[0].replace("n_", ""), fontsize=7)
        ax.set_title(f"threshold vs {label} (averaged over {others[1].replace('n_', '')})")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, help="override n_trials from config.yaml")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    n_trials = args.trials or config["n_trials"]
    sessions_max, delta = config["sweep_sessions_max"], config["sweep_delta"]
    print(cfg_mod.describe_data(config))
    if sessions_max > cfg_mod.max_sessions(config):
        raise SystemExit(f"sweep_sessions_max = {sessions_max} but some user has only "
                         f"{cfg_mod.max_sessions(config)} sessions; lower it in config.yaml")
    out = run / "results" / "sweep"
    out.mkdir(parents=True, exist_ok=True)
    pairs_path, attempts_path = out / "pairs.csv", out / "attempts.csv"
    match_mod.load_cache()

    # Resume: seeds already in pairs.csv are skipped.
    pairs = pd.read_csv(pairs_path) if pairs_path.exists() else pd.DataFrame()
    attempts = pd.read_csv(attempts_path) if attempts_path.exists() else pd.DataFrame()
    done = set(pairs["seed"]) if len(pairs) else set()
    seeds = [config["seed"] + t for t in range(n_trials)]
    for t, seed in enumerate(seeds, 1):
        if seed in done:
            continue
        new_pairs, new_attempts = pair_scores(config, seed, sessions_max)
        pairs = pd.concat([pairs, pd.DataFrame(new_pairs)], ignore_index=True)
        attempts = pd.concat([attempts, pd.DataFrame(new_attempts)], ignore_index=True)
        pairs.to_csv(pairs_path, index=False)
        attempts.to_csv(attempts_path, index=False)
        match_mod.save_cache()
        print(f"draw {t}/{n_trials} (seed {seed}) done", flush=True)
    pairs = pairs[pairs["seed"].isin(seeds) & (pairs["sessions"] <= sessions_max)]
    if len(attempts):
        attempts = attempts[attempts["seed"].isin(seeds) & (attempts["sessions"] <= sessions_max)]

    users_by_seed = {seed: draw(config, seed)[0] for seed in seeds}
    cells = cell_results(pairs, attempts, config, users_by_seed)
    summary = (cells.groupby(["sessions", "n_legit", "n_impostor"])
               .agg(matched_mean=("matched_detected", "mean"), matched_std=("matched_detected", "std"),
                    threshold_mean=("threshold", "mean"), threshold_std=("threshold", "std"),
                    attempt_accept_mean=("attempt_accept_rate", "mean"))
               .round(3).reset_index())
    summary.to_csv(out / "summary.csv", index=False)

    report = []
    for (n_legit, n_impostor), group in summary.groupby(["n_legit", "n_impostor"]):
        flat, jump, size = saturation(group.set_index("sessions")["threshold_mean"], delta)
        report.append({"axis": "sessions", "n_legit": n_legit, "n_impostor": n_impostor, "sessions": None,
                       "flat_from": flat, "biggest_jump_at": jump, "biggest_jump": round(size, 3)})
    for (k, n_impostor), group in summary.groupby(["sessions", "n_impostor"]):
        if len(group) > 1:
            flat, jump, size = saturation(group.set_index("n_legit")["threshold_mean"], delta)
            report.append({"axis": "n_legit", "n_legit": None, "n_impostor": n_impostor, "sessions": k,
                           "flat_from": flat, "biggest_jump_at": jump, "biggest_jump": round(size, 3)})
    for (k, n_legit), group in summary.groupby(["sessions", "n_legit"]):
        if len(group) > 1:
            flat, jump, size = saturation(group.set_index("n_impostor")["threshold_mean"], delta)
            report.append({"axis": "n_impostor", "n_legit": n_legit, "n_impostor": None, "sessions": k,
                           "flat_from": flat, "biggest_jump_at": jump, "biggest_jump": round(size, 3)})
    report = pd.DataFrame(report)
    report.to_csv(out / "saturation.csv", index=False)

    n_users = len(users_by_seed[seeds[0]])
    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    plot_heatmaps(summary, figures / "sweep_heatmaps.png", n_users)
    plot_lines(summary, figures / "sweep_lines.png")
    (out / "settings.json").write_text(json.dumps({"seeds": seeds, "config": config}, indent=2) + "\n")

    for axis, group in report.groupby("axis", sort=False):
        print(f"{axis}: flat (changes < {delta}) from a median of {group['flat_from'].median():g}; "
              f"biggest jump most often at {group['biggest_jump_at'].mode().iloc[0]:g} "
              f"(median size {group['biggest_jump'].median():.2f})")
    if summary["attempt_accept_mean"].notna().any():
        by_k = summary.groupby("sessions")["attempt_accept_mean"].mean()
        print("Balabit impostor attempts accepted, by sessions per user: "
              + ", ".join(f"{k}: {v:.0%}" for k, v in by_k.items()))
    print(f"Cells: {len(summary)}  Draws: {len(seeds)}")
    print(f"Output: {out}, {figures / 'sweep_heatmaps.png'}, {figures / 'sweep_lines.png'}")


if __name__ == "__main__":
    main()
