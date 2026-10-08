#!/usr/bin/env python3
"""Flag anomalous stroke windows against a user's concave hull: own held-out sessions (false rejections) vs other users' sessions."""

import argparse
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from shapely import MultiPoint, concave_hull, contains_xy

cfg_mod = import_module("00_config")
chunk_mod = import_module("03_chunk_shapes")
sample_mod = import_module("01_sample_users")


def end_points(config: dict, user: str, name: str) -> np.ndarray:
    """One point per chunk of a training session: its end once its start is moved to (0, 0)."""
    chunks = chunk_mod.segment(cfg_mod.load_session(cfg_mod.ROOT / config["dataset_dir"] / user / name), config)
    return np.array([chunk[-1, :2] - chunk[0, :2] for chunk, _ in chunks]).reshape(-1, 2)


def build_hull(sessions: list[np.ndarray], config: dict):
    return concave_hull(MultiPoint(np.unique(np.vstack(sessions), axis=0)), ratio=config["concave_ratio"])


def score(hull, points: np.ndarray, config: dict) -> dict:
    """Share of strokes outside the hull, per window of `anomaly_window` strokes; a window is flagged when more
    than `anomaly_outside_share` of it is outside. A session shorter than one window is one window."""
    outside = ~contains_xy(hull, points[:, 0], points[:, 1])
    size = min(config["anomaly_window"], len(outside))
    windows = np.convolve(outside, np.ones(size), "valid") / size if size else np.array([])
    flagged = windows > config["anomaly_outside_share"]
    return {"strokes": len(points), "outside_share": float(outside.mean()) if len(outside) else np.nan,
            "windows": len(windows), "windows_flagged": int(flagged.sum()),
            "max_window_outside": float(windows.max()) if len(windows) else np.nan,
            "session_flagged": bool(flagged.any())}


def equal_error_rate(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """EER on max_window_outside: a session is rejected when its worst window reaches the cut."""
    cuts = np.unique(np.concatenate([genuine, impostor, [np.inf]]))
    rates = np.array([(np.mean(genuine >= t), np.mean(impostor < t)) for t in cuts])  # (FRR, FAR)
    i = int(np.argmin(np.abs(rates[:, 0] - rates[:, 1])))
    return float(rates[i].mean())


def simulate(sessions: pd.DataFrame, config: dict, worst: str, eer) -> pd.DataFrame:
    """The experiment as configured: in each of `n_trials` draws (seed, seed + 1, ...; draw 0 = script 01's draw),
    `n_legitimate` users are the profiles and `n_impostor` other users the impostors. FRR from the legitimate users'
    own held-out sessions, FAR from the drawn impostors' sessions against those profiles, EER on `worst`, all pooled
    over the legitimate users of the draw. Every profile already scored every other user, so a draw only picks rows."""
    if config["n_trials"] < 1:
        raise SystemExit("n_trials must be at least 1")
    rows = []
    for trial in range(config["n_trials"]):
        legitimate, impostors = sample_mod.draw_users(config, config["seed"] + trial)
        g = sessions[sessions["profile"].isin(legitimate)
                     & ((sessions["kind"] == "genuine") | sessions["session_user"].isin(impostors))]
        gen, imp = g[g["kind"] == "genuine"], g[g["kind"] == "impostor"]
        rows.append({"trial": trial, "legitimate": " ".join(legitimate), "impostor": " ".join(impostors),
                     "genuine_sessions": len(gen), "impostor_sessions": len(imp),
                     "frr": gen["session_flagged"].mean(), "far": 1 - imp["session_flagged"].mean(),
                     "eer": eer(gen[worst].to_numpy(), imp[worst].to_numpy())})
    return pd.DataFrame(rows)


def draws_row(draws: pd.DataFrame, config: dict) -> dict:
    """Mean and spread over the draws; the std is NaN with one draw."""
    row = {"profile": f"{config['n_legitimate']} legit + {config['n_impostor']} impostors, {len(draws)} draws",
           "genuine_sessions": round(draws["genuine_sessions"].mean(), 1),
           "impostor_sessions": round(draws["impostor_sessions"].mean(), 1)}
    for rate in ("frr", "far", "eer"):
        row[rate], row[f"{rate}_std"] = round(draws[rate].mean(), 4), round(draws[rate].std(), 4)
    return row


def summarize(sessions: pd.DataFrame, config: dict, worst: str, eer) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per user: the profile against all other users' sessions. Last row: the configured experiment (mean over draws)."""
    summary = []
    for user, g in sessions.groupby("profile"):
        gen, imp = g[g["kind"] == "genuine"], g[g["kind"] == "impostor"]
        summary.append({
            "profile": user, "genuine_sessions": len(gen), "impostor_sessions": len(imp),
            "genuine_outside": round(gen["outside_share"].mean(), 4),
            "impostor_outside": round(imp["outside_share"].mean(), 4),
            "frr": round(gen["session_flagged"].mean(), 4),        # own session flagged at least once
            "far": round(1 - imp["session_flagged"].mean(), 4),    # impostor session never flagged
            "eer": round(eer(gen[worst].to_numpy(), imp[worst].to_numpy()), 4),
        })
    draws = simulate(sessions, config, worst, eer)
    return pd.DataFrame(summary + [draws_row(draws, config)]), draws


def print_summary(summary: pd.DataFrame, what: str) -> None:
    for _, r in summary.iloc[:-1].iterrows():
        print(f"{r['profile']:9} own flagged (FRR) {r['frr']:6.1%} of {int(r['genuine_sessions']):3} | impostor missed (FAR) "
              f"{r['far']:6.1%} of {int(r['impostor_sessions']):3} | strokes {what}: own {r['genuine_outside']:.1%}, "
              f"impostor {r['impostor_outside']:.1%} | EER {r['eer']:.1%}")
    r = summary.iloc[-1]
    print(f"{r['profile']}: FRR {r['frr']:.1%} ± {r['frr_std']:.1%} | FAR {r['far']:.1%} ± {r['far_std']:.1%} | "
          f"EER {r['eer']:.1%} ± {r['eer_std']:.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    users = cfg_mod.list_users(config)
    targets = [u for u in users if not args.user or u in args.user]
    k = config["anomaly_enroll_sessions"]
    print(f"Training sessions only (each certainly its folder's user); hull from {k} sessions, window "
          f"{config['anomaly_window']} strokes, flagged when > {config['anomaly_outside_share']:.0%} outside")

    names = {u: [p.name for p in cfg_mod.list_sessions(config, u)] for u in users}
    ends = {(u, n): end_points(config, u, n) for u in users for n in names[u]}
    rows = []
    for user in targets:
        if len(names[user]) <= k:
            raise SystemExit(f"{user} has {len(names[user])} training sessions; anomaly_enroll_sessions must be lower")
        # Genuine: leave one training session out, build the hull from k of the others, test the left-out one.
        for test in names[user]:
            others = [n for n in names[user] if n != test]
            enroll = random.Random(f"{config['seed']}-{user}-{test}").sample(others, k)
            hull = build_hull([ends[(user, n)] for n in enroll], config)
            rows.append({"profile": user, "session_user": user, "session": test, "kind": "genuine",
                         **score(hull, ends[(user, test)], config)})
        # Impostor: the user's hull from k sessions against every training session of the other users.
        enroll = random.Random(f"{config['seed']}-{user}").sample(names[user], k)
        hull = build_hull([ends[(user, n)] for n in enroll], config)
        for other in users:
            if other != user:
                rows += [{"profile": user, "session_user": other, "session": n, "kind": "impostor",
                          **score(hull, ends[(other, n)], config)} for n in names[other]]

    sessions = pd.DataFrame(rows)
    summary, draws = summarize(sessions, config, "max_window_outside", equal_error_rate)

    out = run / "results" / "anomaly"
    out.mkdir(parents=True, exist_ok=True)
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
    axes[0].set_xlabel(f"worst window: share of {config['anomaly_window']} strokes outside the hull")
    axes[0].set_ylabel("density")
    axes[0].legend(fontsize=8)
    axes[0].set_title("Genuine vs impostor sessions")
    per_user = summary.iloc[:-1].set_index("profile")
    x = np.arange(len(per_user))
    axes[1].bar(x - 0.2, per_user["frr"] * 100, 0.4, color="tab:blue", label="own sessions flagged (FRR)")
    axes[1].bar(x + 0.2, per_user["far"] * 100, 0.4, color="tab:red", label="impostor sessions not flagged (FAR)")
    axes[1].set_xticks(x, per_user.index, rotation=45)
    axes[1].set_ylabel("%")
    axes[1].set_ylim(0, 105)
    axes[1].legend(fontsize=8)
    axes[1].set_title("Per user (profile vs all other users)")
    pooled = summary.iloc[-1]
    fig.suptitle(f"Concave-hull anomaly test: hull from {k} sessions, window {config['anomaly_window']}, "
                 f"flag > {config['anomaly_outside_share']:.0%} outside; {pooled['profile']}: "
                 f"EER {pooled['eer']:.1%} ± {pooled['eer_std']:.1%}")
    fig.tight_layout()
    fig.savefig(figures / "hull_anomaly.png", dpi=130)
    plt.close(fig)

    print_summary(summary, "outside")
    print(f"Output: {out}, {figures / 'hull_anomaly.png'}")


if __name__ == "__main__":
    main()
