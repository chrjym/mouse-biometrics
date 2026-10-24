#!/usr/bin/env python3
"""Short strokes (~0.5 s) for user29 and user20: cut move strokes into 0.5 s pieces, put each at (0,0),
enrol a hull region from the first 4 sessions, then score test sessions by the share of pieces inside it."""
import sys
from importlib import import_module
from pathlib import Path
import numpy as np, pandas as pd, matplotlib, shapely
from shapely.geometry import MultiPoint
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shapes_explore/scripts"))
from chain_shape import cfg_mod, K
ch = import_module("03_chunk_shapes")
RUN = cfg_mod.ROOT / "runs/efdc92"; OUT = Path(__file__).parent
USERS, PIECE, MIN_PTS, INSIDE = ["user29", "user20"], 0.5, 4, 0.9

def pieces(user, session, folder, config):
    """Move strokes of one session cut into PIECE-second pieces, each shifted to start at (0,0)."""
    out = []
    for c, kind in ch.segment(cfg_mod.load_session(cfg_mod.ROOT / folder / user / session), config):
        if kind != ch.MOVE or ch.normalize(c, config["resample_n"]) is None: continue
        cut = ((c[:, 2] - c[0, 2]) // PIECE).astype(int)
        for k in np.unique(cut):
            q = c[cut == k]
            if len(q) >= MIN_PTS and np.ptp(q[:, :2], axis=0).max() > 0: out.append(q[:, :2] - q[0, :2])
    return out

def region(ps):
    cloud = MultiPoint(np.vstack(ps)); return shapely.concave_hull(cloud, ratio=.15), cloud.convex_hull

def share_inside(ps, poly):
    """Share of pieces with >= INSIDE of their points inside poly."""
    shapely.prepare(poly)
    return np.mean([shapely.contains_xy(poly, p[:, 0], p[:, 1]).mean() >= INSIDE for p in ps])

def main():
    config = cfg_mod.load_config(RUN / "1_9_0.04_4/config.yaml"); data = {}
    for u in USERS:
        order = cfg_mod.session_pool(config, u, config["seed"])
        data[u] = {"enrol": [p for f, n in order[:K] for p in pieces(u, n, f, config)],
                   "test": [(n, pieces(u, n, f, config)) for f, n in order[-K:]]}
    rows, meta = [], []
    for u in USERS:
        e = data[u]["enrol"]; dur = len(e)
        meta.append({"user": u, "enrol_pieces": len(e), "reach_median_px": np.median([np.hypot(*p.T).max() for p in e]),
                     "points_per_piece": np.median([len(p) for p in e])})
        conc, conv = region(e); data[u]["region"] = (conc, conv)
        for v in USERS:
            for n, ps in data[v]["test"]:
                rows.append({"profile": u, "tested": v, "kind": "legitimate" if u == v else "impostor", "session": n,
                             "pieces": len(ps), "inside_concave": share_inside(ps, conc), "inside_convex": share_inside(ps, conv)})
    t = pd.DataFrame(rows); t.to_csv(OUT / "scores.csv", index=False)
    m = pd.DataFrame(meta)
    m["concave_k_px2"] = [data[u]["region"][0].area / 1e3 for u in USERS]; m["convex_k_px2"] = [data[u]["region"][1].area / 1e3 for u in USERS]
    m.to_csv(OUT / "regions.csv", index=False); print(m.round(1).to_string(index=False)); print(t.round(3).to_string(index=False))
    a, b = data["user29"]["region"][0], data["user20"]["region"][0]
    print(f"concave IoU {a.intersection(b).area / a.union(b).area:.2f}")
    # figure: row per user: enrol pieces + regions, legit vs impostor test pieces; last panel: scores
    fig, axs = plt.subplots(2, 3, figsize=(20, 13)); col = {"user29": "tab:blue", "user20": "tab:orange"}
    lim = max(np.abs(np.vstack(data[u]["enrol"])).max() for u in USERS) * 1.05
    for r, u in enumerate(USERS):
        conc, conv = data[u]["region"]; other = USERS[1 - r]
        for ax, (title, ps, c) in zip(axs[r], [(f"{u} enrolment: {len(data[u]['enrol'])} pieces of 0.5 s (first {K} sessions)", data[u]["enrol"], col[u]),
                                              (f"{u} own test sessions (last {K})", [p for _, q in data[u]["test"] for p in q], col[u]),
                                              (f"{other} test sessions against {u}'s region", [p for _, q in data[other]["test"] for p in q], col[other])]):
            for p in ps: ax.plot(p[:, 0], p[:, 1], color=c, lw=.4, alpha=.35)
            ax.fill(*conc.exterior.xy, color="k", alpha=.07); ax.plot(*conc.exterior.xy, "k", lw=1.8, label=f"concave 0.15 ({conc.area/1e3:,.0f}k px²)")
            ax.plot(*conv.exterior.xy, "k--", lw=1, label=f"convex ({conv.area/1e3:,.0f}k px²)")
            ax.plot(0, 0, "ro"); ax.set_xlim(-lim, lim); ax.set_ylim(lim, -lim); ax.set_aspect("equal"); ax.set_title(title, fontsize=10); ax.legend(loc="lower right", fontsize=8)
    fig.suptitle("Short strokes (0.5 s pieces) at (0,0): enrolment region of each user, and test pieces from both users (px)"); fig.tight_layout()
    fig.savefig(OUT / "short_strokes_regions.png", dpi=90); plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), sharey=True)
    for ax, u in zip(axs, USERS):
        g = t[t.profile == u]; x = np.arange(K)
        for kind, off, c in [("legitimate", -.2, "tab:green"), ("impostor", .2, "tab:red")]:
            s = g[g.kind == kind]; ax.bar(x + off, s.inside_concave, .4, color=c, label=f"{kind} ({s.tested.iloc[0]})")
        ax.axhline(t[(t.profile == u) & (t.kind == "legitimate")].inside_concave.min(), color="grey", ls=":", lw=1)
        ax.set_xticks(x, [f"test {i+1}" for i in x]); ax.set_title(f"against {u}'s concave region"); ax.legend(fontsize=8); ax.grid(alpha=.3, axis="y")
    axs[0].set_ylabel(f"share of pieces inside (≥{INSIDE:.0%} of points)"); fig.suptitle("Test sessions: share of 0.5 s pieces inside the enrolment region")
    fig.tight_layout(); fig.savefig(OUT / "short_strokes_scores.png", dpi=110); plt.close(fig)

if __name__ == "__main__":
    main()
