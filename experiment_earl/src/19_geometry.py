#!/usr/bin/env python3
"""Closed-form geometric measures per stroke (straightness, chord deviation, Menger curvature, overshoot, hull fill)
and whether they tell users apart: per-feature spread across users and a verification EER per feature and combined.
Same session draw as 18: profile = first `sessions` of each user's pool, genuine test = last `sessions`, impostor test =
sessions `sessions`..2*`sessions` of every other user. Writes runs/geometry_<sessions>/."""

import argparse
from importlib import import_module

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull
from scipy.stats import kruskal, ks_2samp

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
hull_mod = import_module("18_hull_profile")

FEATURES = {
    "straightness": "chord / path length (1 = straight)",
    "chord_deviation": "largest distance from the chord / chord",
    "bow_side": "mean signed distance from the chord / chord (+ = bows left of travel)",
    "curvature_mean": "mean Menger curvature (1 / radius)",
    "curvature_peak": "90th percentile Menger curvature",
    "overshoot": "how far the path passes the end point along the chord / chord",
    "hull_fill": "area of the stroke's own convex hull / chord^2",
}


def menger(path: np.ndarray) -> np.ndarray:
    """Menger curvature 4·area / (|ab|·|bc|·|ca|) of every three consecutive points."""
    a, b, c = path[:-2], path[1:-1], path[2:]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    sides = np.hypot(*(b - a).T) * np.hypot(*(c - b).T) * np.hypot(*(c - a).T)
    return np.divide(2 * np.abs(cross), sides, out=np.zeros(len(cross)), where=sides > 1e-12)


def measures(path: np.ndarray) -> dict | None:
    """Every feature of one normalized path (starts at (0, 0)); None when it ends where it started."""
    chord = np.hypot(*path[-1])
    if chord < 1e-6:
        return None
    turned = hull_mod.rotate(path[None])[0] / chord     # chord along +x, length 1
    arc = np.hypot(*np.diff(path, axis=0).T).sum()
    k = menger(turned)
    try:
        fill = ConvexHull(turned).volume
    except Exception:                                    # all points on one line
        fill = 0.0
    return {"straightness": chord / arc, "chord_deviation": np.abs(turned[:, 1]).max(),
            "bow_side": turned[:, 1].mean(), "curvature_mean": k.mean(), "curvature_peak": np.quantile(k, 0.9),
            "overshoot": max(turned[:, 0].max() - 1, 0.0), "hull_fill": fill}


def session_table(session) -> pd.DataFrame:
    rows = [m for paths in session.paths.values() for p in paths if (m := measures(p))]
    return pd.DataFrame(rows, columns=list(FEATURES))


def draw(config: dict, k: int) -> dict:
    """Per user: (enrolled, genuine test, impostor test) lists of per-session feature tables."""
    out = {}
    for u in cfg_mod.list_users(config):
        pool = cfg_mod.session_pool(config, u, config["seed"])
        load = lambda pairs: [session_table(match_mod.dataset_session(u, n, config, f)) for f, n in pairs]
        out[u] = (load(pool[:k]), load(pool[-k:]), load(pool[k:2 * k]))
    return out


def distance(session: pd.DataFrame, profile: pd.DataFrame, features: list[str]) -> float:
    """Mean Kolmogorov–Smirnov statistic between the session's and the profile's strokes (0 = same distribution)."""
    if len(session) < 5:
        return 1.0
    return float(np.mean([ks_2samp(session[f], profile[f]).statistic for f in features]))


def eer(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """Equal error rate for distances (accept when distance <= t)."""
    rates = [((genuine > t).mean(), (impostor <= t).mean()) for t in np.unique(np.concatenate([genuine, impostor]))]
    frr, far = min(rates, key=lambda r: abs(r[0] - r[1]))
    return (frr + far) / 2


def verify(data: dict, features: list[str]) -> float:
    genuine, impostor = [], []
    for p, (enrolled, own, _) in data.items():
        profile = pd.concat(enrolled)
        genuine += [distance(s, profile, features) for s in own]
        impostor += [distance(s, profile, features) for v, (_, _, other) in data.items() if v != p for s in other]
    return eer(np.array(genuine), np.array(impostor))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"geometry_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)

    rows, first = [], None
    for seed in args.seeds:
        config["seed"] = seed
        data = draw(config, args.sessions)
        first = first or data
        for f in list(FEATURES) + ["all"]:
            rows.append({"seed": seed, "feature": f, "eer": verify(data, list(FEATURES) if f == "all" else [f])})
        print(f"seed {seed}: combined EER {rows[-1]['eer']:.1%}")
    result = pd.DataFrame(rows).groupby("feature")["eer"].agg(["mean", "std"]).sort_values("mean")

    strokes = pd.concat([t.assign(user=u) for u, (enrolled, _, _) in first.items() for t in enrolled])
    spread = {}
    for f in FEATURES:
        groups = [g[f].to_numpy() for _, g in strokes.groupby("user")]
        h = kruskal(*groups).statistic
        spread[f] = (h - len(groups) + 1) / (len(strokes) - len(groups))   # epsilon-squared effect size
    result["between_user_effect"] = pd.Series(spread)
    result.round(4).to_csv(out / "summary.csv")
    strokes.to_csv(out / "strokes_seed{}.csv".format(args.seeds[0]), index=False)
    print(result.round(3).to_string())

    users = sorted(strokes.user.unique(), key=lambda u: int(u[4:]))
    fig, axes = plt.subplots(len(FEATURES), 1, figsize=(10, 2.1 * len(FEATURES)), sharex=True)
    for ax, (f, label) in zip(axes, FEATURES.items()):
        data_f = [strokes.loc[strokes.user == u, f] for u in users]
        lo, hi = np.quantile(strokes[f], [0.02, 0.98])
        ax.boxplot(data_f, showfliers=False)
        ax.set_ylim(lo, hi)
        ax.set_ylabel(f, fontsize=8)
        ax.set_title(f"{label}  ·  EER {result.loc[f, 'mean']:.1%}  ·  effect {spread[f]:.3f}", fontsize=8, loc="left")
    axes[-1].set_xticks(range(1, len(users) + 1), users)
    fig.suptitle(f"Geometric measures per user ({args.sessions} enrolled sessions, seed {args.seeds[0]})")
    fig.tight_layout(); fig.savefig(out / "figures" / "features_by_user.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(result.index, result["mean"] * 100, xerr=result["std"] * 100, color="#4c78a8")
    ax.axvline(50, color="k", ls="--", lw=1, label="chance (50%)")
    ax.axvline(45.4, color="#e45756", ls=":", lw=1.5, label="convex hull (45.4%)")
    ax.set_xlabel(f"EER % (mean ± std over {len(args.seeds)} draws, lower is better)"); ax.invert_yaxis(); ax.legend()
    fig.tight_layout(); fig.savefig(out / "figures" / "eer_by_feature.png", dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
