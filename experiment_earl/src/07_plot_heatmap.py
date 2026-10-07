#!/usr/bin/env python3
"""Heatmap of the mean threshold over sessions per user (rows) x legitimate users (columns)."""

import argparse
import csv
import json
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
threshold_mod = import_module("05_threshold")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = cfg_mod.load_config()
    config["n_impostor"] = config["grid_impostors"]
    match_mod.load_cache()

    sessions, legit_users = config["grid_sessions"], config["grid_legit_users"]
    mean = np.zeros((len(sessions), len(legit_users)))
    std = np.zeros_like(mean)
    for r, n_sessions in enumerate(sessions):
        for c, n_legit in enumerate(legit_users):
            config["sessions_per_user"], config["n_legitimate"] = n_sessions, n_legit
            values = [
                threshold_mod.compute_threshold(
                    match_mod.run_trial(config, config["seed"] + k)["records"], config["n_impostor"])[1]
                for k in range(config["n_trials"])
            ]
            mean[r, c], std[r, c] = np.mean(values), np.std(values)
            print(f"sessions {n_sessions}, legit users {n_legit}: threshold {mean[r, c]:.2f} ± {std[r, c]:.2f}", flush=True)
        match_mod.save_cache()

    results = cfg_mod.ROOT / "results"
    for name, matrix in (("heatmap_matrix.csv", mean), ("heatmap_std.csv", std)):
        with (results / name).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["sessions \\ legit_users"] + legit_users)
            for n_sessions, row in zip(sessions, matrix):
                writer.writerow([n_sessions] + [f"{v:.4f}" for v in row])

    levels = np.round(np.arange(0, 1.01, 0.1), 1)
    fig, ax = plt.subplots(figsize=(7, 5))
    image = ax.imshow(mean, cmap="YlOrRd", norm=BoundaryNorm(levels, 256), origin="lower", aspect="auto")
    ax.set_xticks(range(len(legit_users)), legit_users)
    ax.set_yticks(range(len(sessions)), sessions)
    for r in range(len(sessions)):
        for c in range(len(legit_users)):
            ax.text(c, r, f"{mean[r, c]:.2f}\n±{std[r, c]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_xlabel("number of legitimate users")
    ax.set_ylabel("number of sessions per user")
    ax.set_title(f"Mean threshold (impostors matched / {config['n_impostor']}), {config['n_trials']} trials; 0 = best")
    fig.colorbar(image, ax=ax, ticks=levels, label="threshold")
    fig.tight_layout()
    out = cfg_mod.ROOT / "figures" / "heatmap.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    out.with_suffix(".json").write_text(json.dumps({"config": config}, indent=2) + "\n")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
