#!/usr/bin/env python3
"""Sweep sensitivity x library size for every fixed split of config.yaml and count one confusion matrix per setting into runs/<hash>/sweep/."""

import argparse
import shutil
import time
from importlib import import_module

import numpy as np
import pandas as pd
import yaml

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
plot_mod = import_module("08_plot_matches")
cohort_mod = import_module("13_cohort_score")

SPLIT = ["n_legitimate", "n_impostor"]


def user_order(user: str) -> tuple:
    """user9 before user15."""
    return len(user), user


def sensitivities(config: dict) -> np.ndarray:
    start, stop, step = config["sweep_sensitivity"]
    return np.round(np.arange(start, stop + step / 2, step), 6)


def draw_split(config: dict, n_legit: int, n_impostor: int) -> tuple[list[str], list[str], dict]:
    """The notebook's draw for one split: a fresh RNG from `seed` picks the users, each user's pool is shuffled by
    `seed`. Only the users depend on the seed; the split itself is fixed by config.yaml."""
    split_config = dict(config, n_legitimate=n_legit, n_impostor=n_impostor)
    legit, impostor, order = plot_mod.draw_users(split_config, config["seed"])
    return sorted(legit, key=user_order), sorted(impostor, key=user_order), order


def accepted(query, library: list, sens: np.ndarray, config: dict, cap: float) -> np.ndarray:
    """(library size, sensitivity) -> does `query` pass a library made of the first k sessions of `library`?
    Each stroke's nearest DTW cost per point is computed once per library session; the library of k sessions is
    the running minimum over its sessions, and each sensitivity is a cut on that."""
    nearest = np.array([cohort_mod.library_nearest(query, ("session", s.key), s.paths, config, cap)
                        for s in library])
    if nearest.size == 0:  # no comparable stroke: the session never passes
        return np.zeros((len(library), len(sens)), dtype=bool)
    best = np.minimum.accumulate(nearest, axis=0)
    matched = (best[:, :, None] <= sens).sum(axis=1)
    return matched / max(query.n_chunks, 1) >= config["match_shape_ratio"]


def sweep_split(config: dict, n_legit: int, n_impostor: int, sens: np.ndarray,
                cap: float) -> tuple[pd.DataFrame, dict]:
    """One row per (library size, sensitivity), each counted from scratch over every test session of the split:
    legitimate = a user's last `sweep_test_sessions` sessions against their own library, impostor = an impostor's
    first `sweep_test_sessions` sessions, accepted when they pass any one legitimate library. Positive = impostor."""
    k_max, n_test = config["sweep_sessions_max"], config["sweep_test_sessions"]
    legit, impostor, order = draw_split(config, n_legit, n_impostor)

    def session(user: str, entry: tuple[str, str]):
        folder, name = entry
        return match_mod.dataset_session(user, name, config, folder)

    libraries = {u: [session(u, e) for e in order[u][:k_max]] for u in legit}
    legit_ok = np.array([accepted(session(u, e), libraries[u], sens, config, cap)
                         for u in legit for e in order[u][-n_test:]])
    impostor_ok = np.array([np.logical_or.reduce([accepted(session(v, e), libraries[u], sens, config, cap)
                                                  for u in legit])
                            for v in impostor for e in order[v][:n_test]])

    tn = legit_ok.sum(axis=0)
    fn = impostor_ok.sum(axis=0)
    fp, tp = len(legit_ok) - tn, len(impostor_ok) - fn
    k, s = np.meshgrid(np.arange(1, k_max + 1), sens, indexing="ij")
    table = pd.DataFrame({"n_legitimate": n_legit, "n_impostor": n_impostor, "sessions": k.ravel(),
                          "sensitivity": s.ravel(), "tp": tp.ravel(), "fp": fp.ravel(), "fn": fn.ravel(),
                          "tn": tn.ravel()})
    table["far"] = table.fn / (table.tp + table.fn)
    table["frr"] = table.fp / (table.fp + table.tn)
    table["balanced_accuracy"] = 1 - (table.far + table.frr) / 2
    table["accuracy"] = (table.tp + table.tn) / (table.tp + table.fp + table.fn + table.tn)
    users = {"n_legitimate": n_legit, "n_impostor": n_impostor, "legitimate": " ".join(legit),
             "impostors": " ".join(impostor), "legitimate_sessions": len(legit_ok),
             "impostor_sessions": len(impostor_ok)}
    return table, users


def equal_error(part: pd.DataFrame) -> float:
    """Where FAR meets FRR along the sensitivity grid (mean of the two at the closest sensitivity)."""
    i = (part.far - part.frr).abs().to_numpy().argmin()
    return float((part.far.iloc[i] + part.frr.iloc[i]) / 2)


def pick_best(table: pd.DataFrame) -> pd.DataFrame:
    """Highest balanced accuracy per split; ties go to fewer sessions, then the lower sensitivity. EER is taken
    over the sensitivities at the best library size. Many cells tie exactly (2 vs 3 on seed 945: 11 cells at 0.504)."""
    ranked = (table.assign(score=table.balanced_accuracy.round(9))
              .sort_values(SPLIT + ["score", "sessions", "sensitivity"], ascending=[True, True, False, True, True]))
    best = ranked.groupby(SPLIT, as_index=False, sort=False).head(1).drop(columns="score").reset_index(drop=True)
    best["eer"] = [equal_error(table[(table.n_legitimate == r.n_legitimate) & (table.n_impostor == r.n_impostor)
                                     & (table.sessions == r.sessions)].sort_values("sensitivity"))
                   for r in best.itertuples()]
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    config = cfg_mod.load_config()
    missing = [key for key in cfg_mod.SWEEP_KEYS if key not in config]
    if missing:
        raise SystemExit(f"config.yaml has no {', '.join(missing)}")
    k_max, n_test = config["sweep_sessions_max"], config["sweep_test_sessions"]
    if k_max + n_test > cfg_mod.max_sessions(config):
        raise SystemExit(f"sweep_sessions_max + sweep_test_sessions = {k_max + n_test} but some user has only "
                         f"{cfg_mod.max_sessions(config)} sessions; lower them in config.yaml")
    for n_legit, n_impostor in config["splits"]:
        if n_legit + n_impostor > len(cfg_mod.list_users(config)):
            raise SystemExit(f"Split [{n_legit}, {n_impostor}] needs more users than the data has")
    sens = sensitivities(config)
    cap = round(float(sens[-1] + config["sweep_sensitivity"][2]), 6)  # above every sensitivity: a capped stroke never matches
    print(cfg_mod.describe_data(config))
    cohort_mod.load_nearest()

    tables, users = [], []
    for n_legit, n_impostor in config["splits"]:
        start = time.time()
        table, drawn = sweep_split(config, n_legit, n_impostor, sens, cap)
        cohort_mod.save_nearest()
        tables.append(table)
        users.append(drawn)
        print(f"{n_legit} vs {n_impostor}: legitimate {drawn['legitimate']} | impostors {drawn['impostors']} "
              f"({drawn['legitimate_sessions']} + {drawn['impostor_sessions']} test sessions, "
              f"{time.time() - start:.0f} s)", flush=True)
    table = pd.concat(tables, ignore_index=True)
    best = pick_best(table).set_index(SPLIT).loc[[tuple(s) for s in config["splits"]]].reset_index()

    out = cfg_mod.RUNS / cfg_mod.run_folder_name(config).split("/")[0] / "sweep"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    table.to_csv(out / "confusion.csv", index=False)
    best.to_csv(out / "best.csv", index=False)
    pd.DataFrame(users).to_csv(out / "splits.csv", index=False)

    columns = SPLIT + ["sensitivity", "sessions", "tp", "fp", "fn", "tn", "far", "frr", "balanced_accuracy", "eer"]
    print(best[columns].round(3).to_string(index=False))
    print(f"Settings: {len(table):,} ({len(config['splits'])} splits x {k_max} library sizes x {len(sens)} sensitivities)")
    print(f"Output: {out}/ (confusion.csv, best.csv, splits.csv, config.yaml)")


if __name__ == "__main__":
    main()
