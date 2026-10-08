#!/usr/bin/env python3
"""Randomly draw sessions per selected user, copy them into temp/, and record them in the manifest."""

import argparse
import json
import random
import shutil
from importlib import import_module

cfg_mod = import_module("00_config")


def draw_sessions(config: dict, seed: int, users: list[str]) -> dict[str, dict[str, list[str]]]:
    """Per user, the chosen session names plus the rest as held-out sessions."""
    drawn = {}
    for user in users:
        names = [path.name for path in cfg_mod.list_sessions(config, user)]
        rng = random.Random(f"{seed}-{user}")
        chosen = sorted(rng.sample(names, min(config["sessions_per_user"], len(names))))
        drawn[user] = {"sessions": chosen, "held_out": [n for n in names if n not in chosen]}
    return drawn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    temp = run / "temp"
    manifest_path = temp / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    # Only our own folders are cleared: temp/ also holds Earl's tracked prototype files.
    for label in ("legitimate", "impostor"):
        shutil.rmtree(temp / label, ignore_errors=True)
    manifest["sessions"] = {}
    for label in ("legitimate", "impostor"):
        drawn = draw_sessions(config, manifest["seed"], manifest[label])
        for user, info in drawn.items():
            target = temp / label / user
            target.mkdir(parents=True, exist_ok=True)
            for name in info["sessions"]:
                shutil.copy2(cfg_mod.ROOT / config["dataset_dir"] / user / name, target / name)
            print(f"{label:10} {user:7} {len(info['sessions'])} sessions ({len(info['held_out'])} held out)")
        manifest["sessions"][label] = drawn
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Output: {temp}")


if __name__ == "__main__":
    main()
