#!/usr/bin/env python3
"""Sessions that go through (fixed counts, as in the notebook), per user, for every run under runs/<hash>/: writes accuracy.csv with one row per run and user."""

import argparse
from importlib import import_module
from pathlib import Path

import pandas as pd

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("08_plot_matches")

ROOT = Path(__file__).resolve().parents[1]


def score(user: str, sessions: list[tuple[str, str]], library: list, config: dict) -> dict:
    """Sessions of `user` that pass (>= match_shape_ratio of their strokes match the library), plus the strokes."""
    passed = matched = strokes = 0
    for folder, name in sessions:
        session = match_mod.dataset_session(user, name, config, folder)
        hits = match_mod.matched_chunks(session, library, config)
        passed += hits / max(session.n_chunks, 1) >= config["match_shape_ratio"]
        matched += hits
        strokes += session.n_chunks
    return {"passed": passed, "tested": len(sessions), "matched_strokes": matched, "strokes": strokes}


def score_run(folder: Path) -> list[dict]:
    """Every user's row of one run folder, scored with the folder's own config snapshot."""
    return score_config(cfg_mod.load_config(folder / "config.yaml"), folder.name)


def score_config(config: dict, name: str) -> list[dict]:
    """Legitimate: own last sessions_per_user pool sessions (never in a profile) against own profile. Impostor: first
    sessions_per_user sessions (the notebook's) against the legitimate profile that passes most of them."""
    k = config["sessions_per_user"]
    legit, impostor, order = plot_mod.draw_users(config, config["seed"])
    libraries = {u: [match_mod.dataset_session(u, n, config, f) for f, n in order[u][:k]] for u in legit}
    run = {"run": name, "sensitivity": config["sensitivity"], "sessions": k,
           "n_legitimate": config["n_legitimate"], "n_impostor": config["n_impostor"]}
    rows = []
    for user in legit:
        rows.append({**run, "kind": "legitimate", "user": user, "profile": user,
                     **score(user, order[user][-k:], libraries[user], config)})
    for user in impostor:
        scores = {p: score(user, order[user][:k], lib, config) for p, lib in libraries.items()}
        profile = max(scores, key=lambda p: (scores[p]["passed"], scores[p]["matched_strokes"] / max(scores[p]["strokes"], 1)))
        rows.append({**run, "kind": "impostor", "user": user, "profile": profile, **scores[profile]})
    for row in rows:
        row["through"] = row["passed"] >= config["match_session_ratio"] * row["tested"]
    return rows


def by_sensitivity(folders: list[Path]) -> dict[float, list[Path]]:
    """Run folders grouped by their snapshot's sensitivity, in folder order inside each group."""
    groups: dict[float, list[Path]] = {}
    for folder in folders:
        groups.setdefault(cfg_mod.load_config(folder / "config.yaml")["sensitivity"], []).append(folder)
    return dict(sorted(groups.items()))


def drop_new_pairs(sensitivity: float, known: set) -> None:
    """Forget the pairs computed at `sensitivity` in this script, so memory stays at one sensitivity's worth.
    No pair is shared across sensitivities (it is part of the key), so later groups lose nothing."""
    for key in [k for k in match_mod._PAIRS if k[-1] == sensitivity and k not in known]:
        del match_mod._PAIRS[key]


def finished_part(path: Path, folders: list[Path]) -> pd.DataFrame | None:
    """The saved rows of one sensitivity, if they cover exactly these run folders (else that sensitivity is rescored)."""
    if not path.exists():
        return None
    part = pd.read_csv(path)
    return part if set(part["run"]) == {f.name for f in folders} else None


def save_part(part: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Write via a temporary file, so a kill mid-write never leaves a half file that looks finished."""
    path.parent.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    part.to_csv(tmp, index=False)
    tmp.replace(path)
    return part


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ holding the runs to compare "
                                                "(default: the one config.yaml selects)")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    folders = sorted(p.parent for p in group.glob("*/config.yaml"))
    if not folders:
        raise SystemExit(f"No runs under {group}")
    keep = cfg_mod.load_config()["sensitivity"]

    match_mod.load_cache()
    parts, skipped = [], 0
    for sens, part in by_sensitivity(folders).items():
        path = group / "accuracy_parts" / f"sensitivity_{sens:g}.csv"
        done = finished_part(path, part)
        if done is not None:
            parts.append(done)
            skipped += len(part)
            continue
        known = set(match_mod._PAIRS)
        rows = []
        for folder in part:
            rows += score_run(folder)
            print(f"{folder.name} done", flush=True)
        if sens != keep:
            drop_new_pairs(sens, known)
        parts.append(save_part(pd.DataFrame(rows), path))
    if skipped:
        print(f"Reused {skipped} runs from {group / 'accuracy_parts'}")
    table = pd.concat(parts, ignore_index=True)
    table.to_csv(group / "accuracy.csv", index=False)
    match_mod.save_cache()

    summary = table.groupby(["n_legitimate", "n_impostor", "kind", "sensitivity", "sessions"]).agg(passed=("passed", "sum"), tested=("tested", "sum"),
                                                                     through=("through", "sum"), users=("user", "size"))
    print(summary.to_string())
    print(f"Runs: {len(folders)}  Rows: {len(table)}")
    print(f"Output: {group / 'accuracy.csv'}")


if __name__ == "__main__":
    main()
