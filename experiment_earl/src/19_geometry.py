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


def explain(config: dict, path_out) -> None:
    """One real stroke per panel, turned so its chord runs from (0, 0) to (1, 0), with each measure drawn on it."""
    user = cfg_mod.list_users(config)[0]
    pool = cfg_mod.session_pool(config, user, config["seed"])
    paths = match_mod.dataset_session(user, pool[0][1], config, pool[0][0]).paths[0]
    turned = [hull_mod.rotate(p[None])[0] / np.hypot(*p[-1]) for p in paths if np.hypot(*p[-1]) > 1e-6]
    stats = [measures(p) for p in paths if np.hypot(*p[-1]) > 1e-6]
    # a curved stroke with a visible overshoot shows every measure at once
    pick = max(range(len(turned)), key=lambda i: (0.05 < stats[i]["overshoot"] < 0.4) * (0.4 < stats[i]["straightness"] < 0.8)
               * stats[i]["chord_deviation"] * (stats[i]["chord_deviation"] < 0.6))
    p, m = turned[pick], stats[pick]
    k = menger(p)
    i_dev = np.argmax(np.abs(p[:, 1]))
    hull = ConvexHull(p).vertices

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.5))
    def base(ax, title):
        ax.plot(p[:, 0], p[:, 1], color="#4c78a8", lw=2)
        ax.plot([0, 1], [0, 0], "k--", lw=1, label="chord (start → end)")
        ax.plot(0, 0, "go", ms=8, label="start (0, 0)"); ax.plot(1, 0, "rs", ms=8, label="end (1, 0)")
        ax.set_aspect("equal"); ax.set_title(title, fontsize=10); ax.grid(alpha=0.2)

    base(axes[0, 0], f"Straightness = chord / path length = {m['straightness']:.2f}\n(1 = perfectly straight)")
    axes[0, 0].legend(fontsize=7, loc="best")
    base(axes[0, 1], f"Chord deviation = largest gap from chord = {m['chord_deviation']:.2f}")
    axes[0, 1].annotate("", xy=(p[i_dev, 0], p[i_dev, 1]), xytext=(p[i_dev, 0], 0),
                        arrowprops={"arrowstyle": "<->", "color": "#e45756", "lw": 2})
    base(axes[0, 2], f"Bow side = mean signed gap = {m['bow_side']:+.2f}\n(+ left of travel, − right)")
    axes[0, 2].fill_between(p[:, 0], 0, p[:, 1], where=p[:, 1] > 0, color="#54a24b", alpha=0.3, label="left")
    axes[0, 2].fill_between(p[:, 0], 0, p[:, 1], where=p[:, 1] < 0, color="#e45756", alpha=0.3, label="right")
    axes[0, 2].legend(fontsize=7)
    ax = axes[1, 0]
    sc = ax.scatter(p[1:-1, 0], p[1:-1, 1], c=k, cmap="viridis", s=25, zorder=3)
    ax.plot([0, 1], [0, 0], "k--", lw=1); ax.set_aspect("equal"); ax.grid(alpha=0.2)
    j = np.argmax(k) + 1
    r = 1 / max(k[j - 1], 1e-9)
    a, b, c = p[j - 1], p[j], p[j + 1]
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) > 1e-12:
        ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
        uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
        ax.add_patch(plt.Circle((ux, uy), r, fill=False, color="#e45756", lw=1.5, ls=":"))
    fig.colorbar(sc, ax=ax, shrink=0.7, label="curvature")
    ax.set_title(f"Menger curvature = 1 / radius of circle through 3 points\nmean {m['curvature_mean']:.1f}, "
                 f"peak (90th pct) {m['curvature_peak']:.1f}; red circle = sharpest bend", fontsize=10)
    base(axes[1, 1], f"Overshoot = how far it passes the end = {m['overshoot']:.2f}")
    xmax = p[:, 0].max()
    axes[1, 1].axvline(1, color="grey", lw=0.8); axes[1, 1].axvline(xmax, color="#e45756", lw=0.8)
    axes[1, 1].annotate("", xy=(xmax, -0.05), xytext=(1, -0.05), arrowprops={"arrowstyle": "<->", "color": "#e45756", "lw": 2})
    base(axes[1, 2], f"Hull fill = area of the stroke's convex hull = {m['hull_fill']:.2f}\n(chord length 1)")
    poly = np.vstack([p[hull], p[hull[:1]]])
    axes[1, 2].fill(poly[:, 0], poly[:, 1], color="#f58518", alpha=0.25); axes[1, 2].plot(poly[:, 0], poly[:, 1], color="#f58518")
    for ax in axes.ravel():
        ax.set_xlim(-0.15, max(1.15, xmax + 0.1))
        ax.set_ylim(min(-0.2, p[:, 1].min() - 0.1), max(0.2, p[:, 1].max() + 0.1))
    fig.suptitle(f"What each geometric measure means, on one real stroke of {user} "
                 "(turned so it runs from (0, 0) to (1, 0))")
    fig.tight_layout(); fig.savefig(path_out, dpi=130); plt.close(fig)


def euclidean(data: dict) -> tuple[np.ndarray, np.ndarray]:
    """Genuine and impostor distances: each session = median of every measure, z-scored with the spread of all
    enrolled session medians; profile = mean of the user's enrolled session vectors."""
    median = lambda t: t.median().to_numpy() if len(t) >= 5 else np.full(len(FEATURES), np.nan)
    enrolled = np.array([median(t) for e, _, _ in data.values() for t in e])
    mu, sd = np.nanmean(enrolled, axis=0), np.nanstd(enrolled, axis=0)
    z = lambda t: (median(t) - mu) / sd
    dist = lambda t, c: float(np.linalg.norm(v - c)) if not np.isnan(v := z(t)).any() else np.inf
    genuine, impostor = [], []
    for p, (e, own, _) in data.items():
        centre = np.nanmean([z(t) for t in e], axis=0)
        genuine += [dist(t, centre) for t in own]
        impostor += [dist(t, centre) for v, (_, _, other) in data.items() if v != p for t in other]
    return np.array(genuine), np.array(impostor)


def euclidean_map(data: dict, path_out, seed: int) -> None:
    """Sessions as points (z-scored medians of the 7 measures) projected on the 2 main axes (PCA): per user the
    enrolled sessions joined into a convex hull around the profile centre, with lines (Euclidean distance) from the
    centre to the user's own test sessions and to other users' sessions."""
    median = lambda t: t.median().to_numpy() if len(t) >= 5 else None
    pts = [(u, role, median(t)) for u, (e, own, other) in data.items()
           for role, ts in (("enrolled", e), ("own", own), ("impostor", other)) for t in ts]
    pts = [(u, r, v) for u, r, v in pts if v is not None]
    x = np.array([v for _, _, v in pts])
    enrolled = np.array([v for _, r, v in pts if r == "enrolled"])
    mu, sd = enrolled.mean(axis=0), enrolled.std(axis=0)
    z = (x - mu) / sd
    _, sing, axes_ = np.linalg.svd(z[[r == "enrolled" for _, r, _ in pts]] - 0, full_matrices=False)
    xy = z @ axes_[:2].T
    share = sing[:2] ** 2 / (sing ** 2).sum()
    users = sorted(data, key=lambda u: int(u[4:]))
    cmap = plt.get_cmap("tab10")
    pick = lambda u, r: np.array([xy[i] for i, (v, rr, _) in enumerate(pts) if v == u and rr == r]).reshape(-1, 2)

    fig = plt.figure(figsize=(20, 11))
    grid = fig.add_gridspec(3, 5, width_ratios=[1.6, 1, 1, 1, 1])
    lim = np.quantile(np.abs(xy), 0.98) * 1.15
    over = fig.add_subplot(grid[:, 0])
    for c, u in enumerate(users):
        e = pick(u, "enrolled")
        over.scatter(*e.T, color=cmap(c), s=30, label=u)
        if len(e) >= 3:
            h = np.append(ConvexHull(e).vertices, ConvexHull(e).vertices[0])
            over.fill(*e[h].T, color=cmap(c), alpha=0.12); over.plot(*e[h].T, color=cmap(c), lw=1.5)
        over.plot(*e.mean(axis=0), "*", color=cmap(c), ms=16, mec="k")
    over.set_title("Every user's shape: 4 enrolled sessions joined by a hull, star = profile centre", fontsize=10)
    over.legend(fontsize=8, ncol=2); over.set_aspect("equal"); over.grid(alpha=0.2)
    over.set_xlim(-lim, lim); over.set_ylim(-lim, lim)
    over.set_xlabel(f"axis 1 ({share[0]:.0%} of the spread)"); over.set_ylabel(f"axis 2 ({share[1]:.0%})")

    for c, u in enumerate(users):
        ax = fig.add_subplot(grid[c // 4 if c < 8 else 2, 1 + c % 4]) if c < 8 else fig.add_subplot(grid[2, 1 + (c - 8)])
        e, own = pick(u, "enrolled"), pick(u, "own")
        imp = np.array([xy[i] for i, (v, rr, _) in enumerate(pts) if v != u and rr == "impostor"]).reshape(-1, 2)
        centre = e.mean(axis=0)
        for q in imp:
            ax.plot(*np.array([centre, q]).T, color="#e45756", lw=0.4, alpha=0.35)
        for q in own:
            ax.plot(*np.array([centre, q]).T, color="#4c78a8", lw=1.6)
        ax.scatter(*imp.T, color="#e45756", s=8, alpha=0.6)
        ax.scatter(*own.T, color="#4c78a8", s=40, marker="D", zorder=3)
        if len(e) >= 3:
            h = np.append(ConvexHull(e).vertices, ConvexHull(e).vertices[0])
            ax.fill(*e[h].T, color=cmap(c), alpha=0.2); ax.plot(*e[h].T, color=cmap(c), lw=1.5)
        ax.scatter(*e.T, color=cmap(c), s=25, zorder=3)
        ax.plot(*centre, "*", color=cmap(c), ms=15, mec="k", zorder=4)
        d_own = np.linalg.norm(own - centre, axis=1).mean() if len(own) else np.nan
        d_imp = np.linalg.norm(imp - centre, axis=1).mean()
        ax.set_title(f"{u}: own {d_own:.1f} vs impostor {d_imp:.1f}", fontsize=9,
                     color="#2a7a2a" if d_own < d_imp else "#b22222")
        ax.set_aspect("equal"); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.grid(alpha=0.2)
        ax.tick_params(labelsize=7)
    fig.suptitle(f"Euclidean distance on the 7 geometric measures (seed {seed}). Each dot = one session. "
                 "Blue diamonds/lines = the user's own new sessions, red = other users' sessions; "
                 "title = mean distance to the star (green when own sessions are closer)", fontsize=11)
    fig.tight_layout(); fig.savefig(path_out, dpi=120); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4, help="enrollment sessions per user")
    parser.add_argument("--seeds", type=int, nargs="+", default=[945, 946, 947, 948, 949])
    parser.add_argument("--explain", action="store_true", help="only draw figures/measures_explained.png")
    args = parser.parse_args()

    config = cfg_mod.load_config(sessions_per_user=args.sessions)
    out = cfg_mod.RUNS / f"geometry_{args.sessions}"
    (out / "figures").mkdir(parents=True, exist_ok=True)
    if args.explain:
        config["seed"] = args.seeds[0]
        explain(config, out / "figures" / "measures_explained.png")
        print(f"wrote {out / 'figures' / 'measures_explained.png'}")
        return

    rows, first = [], None
    for seed in args.seeds:
        config["seed"] = seed
        data = draw(config, args.sessions)
        first = first or data
        for f in list(FEATURES) + ["all"]:
            rows.append({"seed": seed, "feature": f, "eer": verify(data, list(FEATURES) if f == "all" else [f])})
        g, i = euclidean(data)
        rows.append({"seed": seed, "feature": "euclidean (all)", "eer": eer(g, i)})
        if seed == args.seeds[0]:
            first_dist = (g, i)
            euclidean_map(data, out / "figures" / "euclidean_map.png", seed)
        print(f"seed {seed}: KS combined EER {rows[-2]['eer']:.1%}, Euclidean EER {rows[-1]['eer']:.1%}")
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
    ax.barh(["euclidean (all)"], [result.loc["euclidean (all)", "mean"] * 100], color="#f58518")
    ax.set_xlabel(f"EER % (mean ± std over {len(args.seeds)} draws, lower is better)"); ax.invert_yaxis(); ax.legend()
    fig.tight_layout(); fig.savefig(out / "figures" / "eer_by_feature.png", dpi=130)
    plt.close(fig)

    g, i = first_dist
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = np.linspace(0, np.quantile(np.concatenate([g, i])[np.isfinite(np.concatenate([g, i]))], 0.99), 40)
    ax.hist(i[np.isfinite(i)], bins, alpha=0.6, color="#e45756", density=True, label=f"impostor sessions ({len(i)})")
    ax.hist(g[np.isfinite(g)], bins, alpha=0.6, color="#4c78a8", density=True, label=f"own sessions ({len(g)})")
    ax.set_xlabel("Euclidean distance from the user's profile (z-scored session medians of all 7 measures)")
    ax.set_title(f"Euclidean distance, seed {args.seeds[0]}: EER {result.loc['euclidean (all)', 'mean']:.1%} "
                 f"(mean of {len(args.seeds)} draws); own sessions should sit left", fontsize=9)
    ax.legend(); fig.tight_layout(); fig.savefig(out / "figures" / "euclidean_distances.png", dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
