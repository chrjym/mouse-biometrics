#!/usr/bin/env python3
"""Rerun the hull, One-Class SVM and DTW anomaly tests with 1 up to `anomaly_enroll_sessions` registered sessions: FRR, FAR and EER per step."""

import argparse
import pickle
import random
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm

cfg_mod = import_module("00_config")
hull_mod = import_module("10_hull_anomaly")
svm_mod = import_module("11_ocsvm_anomaly")
dtw_mod = import_module("12_dtw_anomaly")

# Per method: what is read from a session, how a profile is built from the registered sessions, how a session
# is scored against it, the worst-window column, and whether a high value of that column means "anomalous".
METHODS = {
    "hull": {"prepare": hull_mod.end_points,
             "build": lambda sessions, config, seed: hull_mod.build_hull(sessions, config),
             "score": lambda hull, data, config: hull_mod.score(hull, data, config),
             "worst": "max_window_outside", "high_is_anomalous": True},
    "ocsvm": {"prepare": svm_mod.session_features,
              "build": lambda sessions, config, seed: svm_mod.fit(np.vstack(sessions), config, seed),
              "score": lambda model, data, config: svm_mod.score(model, data, config),
              "worst": "worst_window_score", "high_is_anomalous": False},
    "dtw": {"prepare": dtw_mod.session_shapes,
            "build": dtw_mod.build_library,
            "score": lambda library, data, config: dtw_mod.score(dtw_mod.anomalous(library, *data, config), config),
            "worst": "max_window_outside", "high_is_anomalous": True},
}


def enroll_order(rng: random.Random, sessions: list[str], k_max: int) -> list[str]:
    """The registered sessions in draw order. Python's `sample` on these small lists returns a prefix of the same
    draw for any k, so the first k sessions here are exactly what scripts 10-12 register with k sessions."""
    return rng.sample(sessions, k_max)


def evaluate(method: dict, data: dict, names: dict, user: str, k: int, config: dict) -> list[dict]:
    """The shared protocol of scripts 10-12 for one user with k registered sessions."""
    k_max, rows = config["anomaly_enroll_sessions"], []
    for test in names[user]:  # genuine: leave one out, register k of the others
        seed = f"{config['seed']}-{user}-{test}"
        enroll = enroll_order(random.Random(seed), [n for n in names[user] if n != test], k_max)[:k]
        profile = method["build"]([data[(user, n)] for n in enroll], config, seed)
        rows.append({"profile": user, "session_user": user, "session": test, "kind": "genuine",
                     **method["score"](profile, data[(user, test)], config)})
    seed = f"{config['seed']}-{user}"  # impostor: k registered sessions against every other user's sessions
    enroll = enroll_order(random.Random(seed), names[user], k_max)[:k]
    profile = method["build"]([data[(user, n)] for n in enroll], config, seed)
    for other in names:
        if other != user:
            rows += [{"profile": user, "session_user": other, "session": n, "kind": "impostor",
                      **method["score"](profile, data[(other, n)], config)} for n in names[other]]
    return rows


def rates(g: pd.DataFrame, method: dict) -> dict:
    gen, imp = g[g["kind"] == "genuine"], g[g["kind"] == "impostor"]
    worst_gen, worst_imp = gen[method["worst"]].to_numpy(), imp[method["worst"]].to_numpy()
    eer = (hull_mod.equal_error_rate(worst_gen, worst_imp) if method["high_is_anomalous"]
           else svm_mod.equal_error_rate(worst_gen, worst_imp))
    return {"genuine_sessions": len(gen), "impostor_sessions": len(imp),
            "frr": round(gen["session_flagged"].mean(), 4), "far": round(1 - imp["session_flagged"].mean(), 4),
            "eer": round(eer, 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", action="append", choices=list(METHODS), help="limit to these methods (repeatable)")
    cfg_mod.add_run_argument(parser)
    args = parser.parse_args()
    config, run = cfg_mod.open_run(args.run)
    methods = [m for m in METHODS if not args.method or m in args.method]
    users = cfg_mod.list_users(config)
    names = {u: [p.name for p in cfg_mod.list_sessions(config, u)] for u in users}
    k_max = config["anomaly_enroll_sessions"]
    if min(len(n) for n in names.values()) <= k_max:
        raise SystemExit(f"Some user has only {min(len(n) for n in names.values())} training sessions; "
                         f"anomaly_enroll_sessions must be lower")
    steps = range(1, k_max + 1)
    print(f"Training sessions only; registered sessions 1 to {k_max}; methods {', '.join(methods)}; "
          f"window {config['anomaly_window']} strokes")

    out = run / "results" / "enroll_sweep"
    out.mkdir(parents=True, exist_ok=True)
    progress = out / "progress.pkl"  # finished (method, sessions, user) cells, so an interrupted run continues
    done: dict[tuple, list[dict]] = pickle.loads(progress.read_bytes()) if progress.exists() else {}

    for name in methods:
        method = METHODS[name]
        todo = [(k, u) for k in steps for u in users if (name, k, u) not in done]
        if not todo:
            print(f"{name}: already done", flush=True)
            continue
        data = {(u, n): method["prepare"](config, u, n) for u in users for n in names[u]}
        for k, user in todo:
            done[(name, k, user)] = evaluate(method, data, names, user, k, config)
            progress.write_bytes(pickle.dumps(done))
        print(f"{name} done", flush=True)

    sessions = pd.DataFrame([{"method": m, "enroll_sessions": k, **row}
                             for m in methods for k in steps for u in users for row in done[(m, k, u)]])
    summary = []
    for (m, k), g in sessions.groupby(["method", "enroll_sessions"], sort=False):
        summary.append({"method": m, "enroll_sessions": k, "profile": "all users", **rates(g, METHODS[m])})
        summary += [{"method": m, "enroll_sessions": k, "profile": u, **rates(gu, METHODS[m])}
                    for u, gu in g.groupby("profile")]
    summary = pd.DataFrame(summary)
    sessions.to_csv(out / "sessions.csv", index=False)
    summary.to_csv(out / "summary.csv", index=False)

    pooled = summary[summary["profile"] == "all users"]
    figures = run / "figures"
    figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2), sharey=True)
    for ax, metric, label in zip(axes, ("frr", "far", "eer"),
                                 ("own sessions flagged (FRR)", "impostor sessions not flagged (FAR)", "EER")):
        for m in methods:
            p = pooled[pooled["method"] == m]
            ax.plot(p["enroll_sessions"], p[metric] * 100, marker="o", label=m)
        ax.set_title(label)
        ax.set_xlabel("registered sessions")
        ax.set_xticks(list(steps))
        ax.set_ylim(0, 105)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("% of sessions")
    axes[0].legend(fontsize=8)
    fig.suptitle(f"Anomaly tests by registered sessions (window {config['anomaly_window']}, all users pooled); "
                 f"FRR/FAR at each method's fixed flag rule, EER over all cuts")
    fig.tight_layout()
    fig.savefig(figures / "enroll_sweep_lines.png", dpi=130)
    plt.close(fig)

    grid = pooled.pivot(index="method", columns="enroll_sessions", values="eer").reindex(methods)
    fig, ax = plt.subplots(figsize=(1.6 * len(steps) + 2.5, 0.8 * len(methods) + 1.6))
    image = ax.imshow(grid.to_numpy(), cmap="RdYlGn_r",
                      norm=BoundaryNorm(np.linspace(0, 1, 11), plt.get_cmap("RdYlGn_r").N), aspect="auto")
    for (i, j), value in np.ndenumerate(grid.to_numpy()):
        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=9)
    ax.set_xticks(range(len(steps)), list(steps))
    ax.set_yticks(range(len(methods)), methods)
    ax.set_xlabel("registered sessions")
    ax.set_title("EER (0 = perfect, 0.5 = chance)")
    fig.colorbar(image, ax=ax, ticks=np.linspace(0, 1, 11))
    fig.tight_layout()
    fig.savefig(figures / "enroll_sweep_heatmap.png", dpi=130)
    plt.close(fig)

    for _, r in pooled.iterrows():
        print(f"{r['method']:5} {r['enroll_sessions']} sessions | FRR {r['frr']:6.1%} | FAR {r['far']:6.1%} | EER {r['eer']:6.1%}")
    print(f"Output: {out}, {figures / 'enroll_sweep_lines.png'}, {figures / 'enroll_sweep_heatmap.png'}")


if __name__ == "__main__":
    main()
