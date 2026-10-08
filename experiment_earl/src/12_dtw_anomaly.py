#!/usr/bin/env python3
"""Flag anomalous stroke windows by DTW shape matching against a user's shape library: own held-out sessions (false rejections) vs other users' sessions."""

import argparse
import pickle
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
match_mod = import_module("04_match_shapes")
hull_mod = import_module("10_hull_anomaly")


def session_shapes(config: dict, user: str, name: str) -> tuple[np.ndarray, np.ndarray]:
    """Every comparable chunk of a training session, in order: normalized path (start at the origin, bounding-box
    diagonal 1, `resample_n` points) and kind (move or drag). Chunks too flat to normalize are left out."""
    chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / config["dataset_dir"] / user / name), config)
    shapes = [(chunk_mod.normalize(chunk, config["resample_n"]), kind) for chunk, kind in chunks]
    shapes = [(path, kind) for path, kind in shapes if path is not None]
    paths = np.array([p for p, _ in shapes]).reshape(-1, config["resample_n"], 2)
    return paths, np.array([k for _, k in shapes], dtype=int)


def build_library(sessions: list[tuple[np.ndarray, np.ndarray]], config: dict, seed: str) -> dict[int, np.ndarray]:
    """The user's shapes from the enrolled sessions, at most `dtw_max_library` of them (random), split by kind."""
    paths = np.concatenate([p for p, _ in sessions])
    kinds = np.concatenate([k for _, k in sessions])
    if 0 < config["dtw_max_library"] < len(paths):
        keep = np.array(sorted(random.Random(seed).sample(range(len(paths)), config["dtw_max_library"])))
        paths, kinds = paths[keep], kinds[keep]
    return {kind: np.ascontiguousarray(paths[kinds == kind]) for kind in (chunk_mod.MOVE, chunk_mod.DRAG)}


def anomalous(library: dict[int, np.ndarray], paths: np.ndarray, kinds: np.ndarray, config: dict) -> np.ndarray:
    """Per stroke, in order: True when no library shape of the same kind is within `dtw_tolerance`."""
    n = config["resample_n"]
    band, cap = int(round(config["dtw_band"] * n)), config["dtw_tolerance"] * n
    outside = np.ones(len(paths), dtype=bool)
    for kind, shapes in library.items():
        rows = kinds == kind
        if rows.any() and len(shapes):
            outside[rows] = ~match_mod.has_match(np.ascontiguousarray(paths[rows]), shapes, band, cap)
    return outside


def score(outside: np.ndarray, config: dict) -> dict:
    """Same window rule as the hull test: a window of `anomaly_window` strokes is flagged when more than
    `anomaly_outside_share` of them have no matching shape. A session shorter than one window is one window."""
    size = min(config["anomaly_window"], len(outside))
    windows = np.convolve(outside, np.ones(size), "valid") / size if size else np.array([])
    flagged = windows > config["anomaly_outside_share"]
    return {"strokes": len(outside), "outside_share": float(outside.mean()) if len(outside) else np.nan,
            "windows": len(windows), "windows_flagged": int(flagged.sum()),
            "max_window_outside": float(windows.max()) if len(windows) else np.nan,
            "session_flagged": bool(flagged.any())}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    users = cfg_mod.list_users(config)
    targets = [u for u in users if not args.user or u in args.user]
    k = config["anomaly_enroll_sessions"]
    print(f"Training sessions only; DTW shape matching (tolerance {config['dtw_tolerance']}, library of at most "
          f"{config['dtw_max_library'] or 'all'} shapes); library from {k} sessions, window {config['anomaly_window']} strokes, "
          f"flagged when > {config['anomaly_outside_share']:.0%} have no matching shape")

    out = run / "results" / "dtw"
    out.mkdir(parents=True, exist_ok=True)
    progress = out / "progress.pkl"  # finished profiles, so an interrupted run continues where it stopped
    done: dict[str, list[dict]] = pickle.loads(progress.read_bytes()) if progress.exists() else {}

    names = {u: [p.name for p in cfg_mod.list_sessions(config, u)] for u in users}
    shapes = {(u, n): session_shapes(config, u, n) for u in users for n in names[u]}
    for user in targets:
        if user in done:
            print(f"{user}: already done", flush=True)
            continue
        if len(names[user]) <= k:
            raise SystemExit(f"{user} has {len(names[user])} training sessions; anomaly_enroll_sessions must be lower")
        rows = []
        # Genuine: leave one training session out, library from k of the others (same draw as 10 and 11).
        for test in names[user]:
            others = [n for n in names[user] if n != test]
            enroll = random.Random(f"{config['seed']}-{user}-{test}").sample(others, k)
            library = build_library([shapes[(user, n)] for n in enroll], config, f"{config['seed']}-{user}-{test}")
            rows.append({"profile": user, "session_user": user, "session": test, "kind": "genuine",
                         **score(anomalous(library, *shapes[(user, test)], config), config)})
        # Impostor: the user's library from k sessions against every training session of the other users.
        enroll = random.Random(f"{config['seed']}-{user}").sample(names[user], k)
        library = build_library([shapes[(user, n)] for n in enroll], config, f"{config['seed']}-{user}")
        for other in users:
            if other != user:
                rows += [{"profile": user, "session_user": other, "session": n, "kind": "impostor",
                          **score(anomalous(library, *shapes[(other, n)], config), config)} for n in names[other]]
        done[user] = rows
        progress.write_bytes(pickle.dumps(done))
        print(f"{user} done", flush=True)

    sessions = pd.DataFrame([row for user in targets for row in done[user]])
    summary, draws = hull_mod.summarize(sessions, config, "max_window_outside", hull_mod.equal_error_rate)
    sessions.to_csv(out / "sessions.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    draws.to_csv(out / "draws.csv", index=False)

    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    bins = np.linspace(0, 1, 41)
    for kind, colour in (("genuine", "tab:blue"), ("impostor", "tab:red")):
        axes[0].hist(sessions.loc[sessions["kind"] == kind, "max_window_outside"], bins=bins, alpha=0.6,
                     density=True, color=colour, label=f"{kind} sessions")
    axes[0].axvline(config["anomaly_outside_share"], color="k", linestyle=":", label="anomaly_outside_share")
    axes[0].set_xlabel(f"worst window: share of {config['anomaly_window']} strokes with no matching shape")
    axes[0].set_ylabel("density")
    axes[0].legend(fontsize=8)
    axes[0].set_title("Genuine vs impostor sessions")
    per_user = summary.iloc[:-1].set_index("profile")
    x = np.arange(len(per_user))
    axes[1].bar(x - 0.2, per_user["frr"] * 100, 0.4, color="tab:blue", label="own sessions flagged (FRR)")
    axes[1].bar(x + 0.2, per_user["far"] * 100, 0.4, color="tab:red", label="impostor sessions not flagged (FAR)")
    for i, e in enumerate(per_user["eer"]):
        axes[1].text(i, 102, f"{e:.0%}", ha="center", fontsize=7)
    axes[1].set_xticks(x, per_user.index, rotation=45)
    axes[1].set_ylabel("%  (EER on top)")
    axes[1].set_ylim(0, 110)
    axes[1].legend(fontsize=8, loc="center right")
    axes[1].set_title("Per user (profile vs all other users)")
    pooled = summary.iloc[-1]
    fig.suptitle(f"DTW shape-matching anomaly test (tolerance {config['dtw_tolerance']}): library from {k} sessions, "
                 f"window {config['anomaly_window']}; {pooled['profile']}: EER {pooled['eer']:.1%} ± {pooled['eer_std']:.1%}")
    fig.tight_layout()
    fig.savefig(figures / "dtw_anomaly.png", dpi=130)
    plt.close(fig)

    hull_mod.print_summary(summary, "unmatched")
    print(f"Output: {out}, {figures / 'dtw_anomaly.png'}")


if __name__ == "__main__":
    main()
