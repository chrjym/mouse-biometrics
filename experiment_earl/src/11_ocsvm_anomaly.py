#!/usr/bin/env python3
"""Flag anomalous stroke windows with a per-user One-Class SVM: own held-out sessions (false rejections) vs other users' sessions."""

import argparse
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.svm import OneClassSVM

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
hull_mod = import_module("10_hull_anomaly")

FEATURES = {
    "dx": "net horizontal movement (px)",
    "dy": "net vertical movement (px)",
    "path_length": "log(1 + distance travelled along the path, px)",
    "straightness": "net movement / path length (1 = straight line)",
    "mean_speed": "log(1 + path length / duration, px/s)",
    "duration": "time from the first to the last point (s)",
}


def resample(chunk: np.ndarray, step_s: float) -> np.ndarray:
    """Positions every `step_s` seconds, holding the last logged position, so users whose mouse logs every
    ~16 ms and every ~110 ms give comparable paths. The last point is kept, so dx, dy and duration stay the same."""
    t = np.maximum.accumulate(chunk[:, 2])
    grid = np.append(np.arange(t[0], t[-1], step_s), t[-1])
    return chunk[np.searchsorted(t, grid, side="right") - 1]


def chunk_features(chunk: np.ndarray, step_s: float) -> list[float]:
    path = resample(chunk, step_s) if step_s else chunk
    length = float(np.hypot(*np.diff(path[:, :2], axis=0).T).sum())
    dx, dy = chunk[-1, :2] - chunk[0, :2]
    duration = max(float(chunk[-1, 2] - chunk[0, 2]), 1e-3)
    return [dx, dy, np.log1p(length), np.hypot(dx, dy) / length if length else 0.0,
            np.log1p(length / duration), duration]


def session_features(config: dict, user: str, name: str) -> np.ndarray:
    """One row of the selected features per chunk of a training session."""
    columns = [list(FEATURES).index(f) for f in config["ocsvm_features"]]
    step_s = config["ocsvm_resample_ms"] / 1000
    chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / config["dataset_dir"] / user / name), config)
    rows = np.array([chunk_features(chunk, step_s) for chunk, _ in chunks]).reshape(-1, len(FEATURES))
    return rows[:, columns]


def fit(X: np.ndarray, config: dict, seed: str):
    if 0 < config["ocsvm_max_train"] < len(X):
        X = X[random.Random(seed).sample(range(len(X)), config["ocsvm_max_train"])]
    svm = OneClassSVM(nu=config["ocsvm_nu"], gamma=config["ocsvm_gamma"], kernel="rbf")
    return make_pipeline(RobustScaler(), svm).fit(X)


def score(model, X: np.ndarray, config: dict) -> dict:
    """Mean SVM score per window of `anomaly_window` strokes (> 0 inside the user's region, < 0 outside);
    a window is flagged when its mean is below `ocsvm_flag_score`. A session shorter than one window is one window."""
    scores = model.decision_function(X)
    size = min(config["anomaly_window"], len(scores))
    windows = np.convolve(scores, np.ones(size), "valid") / size if size else np.array([])
    flagged = windows < config["ocsvm_flag_score"]
    return {"strokes": len(X), "outside_share": float(np.mean(scores < 0)) if len(scores) else np.nan,
            "windows": len(windows), "windows_flagged": int(flagged.sum()),
            "worst_window_score": float(windows.min()) if len(windows) else np.nan,
            "session_flagged": bool(flagged.any())}


def equal_error_rate(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """EER on worst_window_score: a session is rejected when its worst window falls below the cut."""
    cuts = np.unique(np.concatenate([genuine, impostor, [np.inf]]))
    rates = np.array([(np.mean(genuine < t), np.mean(impostor >= t)) for t in cuts])  # (FRR, FAR)
    i = int(np.argmin(np.abs(rates[:, 0] - rates[:, 1])))
    return float(rates[i].mean())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    unknown = set(config["ocsvm_features"]) - set(FEATURES)
    if unknown:
        raise SystemExit(f"Unknown ocsvm_features {sorted(unknown)}; choose from {list(FEATURES)}")
    users = cfg_mod.list_users(config)
    targets = [u for u in users if not args.user or u in args.user]
    k = config["anomaly_enroll_sessions"]
    print(f"Training sessions only; One-Class SVM on {', '.join(config['ocsvm_features'])} "
          f"(nu {config['ocsvm_nu']}, gamma {config['ocsvm_gamma']}, resample {config['ocsvm_resample_ms']} ms); "
          f"model from {k} sessions, window {config['anomaly_window']} strokes")

    names = {u: [p.name for p in cfg_mod.list_sessions(config, u)] for u in users}
    features = {(u, n): session_features(config, u, n) for u in users for n in names[u]}
    rows = []
    for user in targets:
        if len(names[user]) <= k:
            raise SystemExit(f"{user} has {len(names[user])} training sessions; anomaly_enroll_sessions must be lower")
        # Genuine: leave one training session out, train on k of the others (same draw as 10_hull_anomaly.py).
        for test in names[user]:
            others = [n for n in names[user] if n != test]
            enroll = random.Random(f"{config['seed']}-{user}-{test}").sample(others, k)
            model = fit(np.vstack([features[(user, n)] for n in enroll]), config, f"{config['seed']}-{user}-{test}")
            rows.append({"profile": user, "session_user": user, "session": test, "kind": "genuine",
                         **score(model, features[(user, test)], config)})
        # Impostor: the user's model from k sessions against every training session of the other users.
        enroll = random.Random(f"{config['seed']}-{user}").sample(names[user], k)
        model = fit(np.vstack([features[(user, n)] for n in enroll]), config, f"{config['seed']}-{user}")
        for other in users:
            if other != user:
                rows += [{"profile": user, "session_user": other, "session": n, "kind": "impostor",
                          **score(model, features[(other, n)], config)} for n in names[other]]
        print(f"{user} done", flush=True)

    sessions = pd.DataFrame(rows)
    summary, draws = hull_mod.summarize(sessions, config, "worst_window_score", equal_error_rate)

    out = run / "results" / "ocsvm"
    out.mkdir(parents=True, exist_ok=True)
    sessions.to_csv(out / "sessions.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)
    draws.to_csv(out / "draws.csv", index=False)

    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    bins = np.linspace(sessions["worst_window_score"].min(), sessions["worst_window_score"].max(), 41)
    for kind, colour in (("genuine", "tab:blue"), ("impostor", "tab:red")):
        axes[0].hist(sessions.loc[sessions["kind"] == kind, "worst_window_score"], bins=bins, alpha=0.6,
                     density=True, color=colour, label=f"{kind} sessions")
    axes[0].axvline(config["ocsvm_flag_score"], color="k", linestyle=":", label="ocsvm_flag_score")
    axes[0].set_xlabel(f"worst window: mean SVM score of {config['anomaly_window']} strokes (higher = more like the user)")
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
    fig.suptitle(f"One-Class SVM anomaly test ({', '.join(config['ocsvm_features'])}): model from {k} sessions, "
                 f"window {config['anomaly_window']}; {pooled['profile']}: EER {pooled['eer']:.1%} ± {pooled['eer_std']:.1%}")
    fig.tight_layout()
    fig.savefig(figures / "ocsvm_anomaly.png", dpi=130)
    plt.close(fig)

    hull_mod.print_summary(summary, "outside")
    print(f"Output: {out}, {figures / 'ocsvm_anomaly.png'}")


if __name__ == "__main__":
    main()
