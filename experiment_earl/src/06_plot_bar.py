#!/usr/bin/env python3
"""Bar graph: impostor users that matched a legitimate profile vs the number of impostor users tested."""

import argparse
import json
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
threshold_mod = import_module("05_threshold")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = cfg_mod.load_config()
    config["n_legitimate"] = config["bar_legit_users"]
    match_mod.load_cache()

    totals, means, stds = config["bar_impostors"], [], []
    for total in totals:
        config["n_impostor"] = total
        detected = [
            threshold_mod.compute_threshold(match_mod.run_trial(config, config["seed"] + k)["records"], total)[0]
            for k in range(config["n_trials"])
        ]
        means.append(np.mean(detected))
        stds.append(np.std(detected))
        print(f"{total} impostor users: matched_detected {means[-1]:.2f} ± {stds[-1]:.2f} over {len(detected)} trials")
    match_mod.save_cache()

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar([str(t) for t in totals], means, yerr=stds, capsize=4, color="tab:blue")
    ax.bar_label(bars, labels=[f"{m:.1f}" for m in means], padding=3)
    ax.set_xlabel("total_number_impostor_user")
    ax.set_ylabel("matched_detected (mean over trials)")
    ax.set_title(f"Impostors matching {config['n_legitimate']} legitimate user(s), {config['sessions_per_user']} sessions each")
    fig.tight_layout()
    out = cfg_mod.ROOT / "figures" / "bar_matched.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=150)
    out.with_suffix(".json").write_text(json.dumps(
        {"totals": totals, "mean": means, "std": stds, "config": config}, indent=2, default=float) + "\n")
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
