#!/usr/bin/env python3
"""Randomly draw sessions per selected user, copy them into temp/, and record them in the manifest."""

import argparse
import json
import shutil
from importlib import import_module

cfg_mod = import_module("00_config")


def draw_sessions(config: dict, seed: int, users: list[str]) -> dict[str, dict[str, list[list[str]]]]:
    """Per user, the first `sessions_per_user` sessions of their shuffled pool (training first, then genuine test
    sessions) and the rest as held-out sessions, each as [folder, name]."""
    drawn = {}
    for user in users:
        pool = [list(entry) for entry in cfg_mod.session_pool(config, user, seed)]
        k = config["sessions_per_user"]
        drawn[user] = {"sessions": pool[:k], "held_out": pool[k:]}
    return drawn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    print(cfg_mod.describe_data(config))
    if config["sessions_per_user"] > cfg_mod.max_sessions(config):
        raise SystemExit(f"sessions_per_user = {config['sessions_per_user']} but some user has only "
                         f"{cfg_mod.max_sessions(config)} sessions; lower it in config.yaml")
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
            for folder, name in info["sessions"]:
                shutil.copy2(cfg_mod.ROOT / folder / user / name, target / name)
            print(f"{label:10} {user:7} {len(info['sessions'])} sessions ({len(info['held_out'])} held out)")
        manifest["sessions"][label] = drawn
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Output: {temp}")


if __name__ == "__main__":
    main()
