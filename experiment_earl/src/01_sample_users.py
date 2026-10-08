#!/usr/bin/env python3
"""Randomly draw the legitimate and impostor users and write temp/manifest.json."""

import argparse
import json
import random
from importlib import import_module

cfg_mod = import_module("00_config")


def draw_users(config: dict, seed: int) -> tuple[list[str], list[str]]:
    users = cfg_mod.list_users(config)
    n_legit, n_impostor = config["n_legitimate"], config["n_impostor"]
    if n_legit + n_impostor > len(users):
        raise SystemExit(
            f"Need {n_legit} legitimate + {n_impostor} impostor users but only {len(users)} exist; "
            "lower n_legitimate or n_impostor in config.yaml"
        )
    rng = random.Random(seed)
    legitimate = sorted(rng.sample(users, n_legit))
    pool = [user for user in users if user not in legitimate]
    return legitimate, sorted(rng.sample(pool, n_impostor))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="override config seed")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    seed = config["seed"] if args.seed is None else args.seed
    legitimate, impostor = draw_users(config, seed)

    manifest_path = run / "temp" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "legitimate": legitimate, "impostor": impostor}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Legitimate: {', '.join(legitimate)}")
    print(f"Impostor:   {', '.join(impostor)}")
    print(f"Output: {manifest_path}")


if __name__ == "__main__":
    main()
