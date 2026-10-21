#!/usr/bin/env python3
"""Convex hulls over ALL sessions of user29 and user20 (every move stroke at (0,0)): nested 50/75/90/100% and concave."""
import sys
from importlib import import_module
from pathlib import Path
import numpy as np, pandas as pd, shapely, matplotlib
from shapely.geometry import MultiPoint
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, "/home/tin/thesis-mouse-biometrics/experiment_earl/src")
cfg_mod = import_module("00_config"); ch = import_module("03_chunk_shapes")
OUT = Path(__file__).parent; USERS = ["user29", "user20"]; COL = {"user29": "tab:blue", "user20": "tab:orange"}; LEVELS = [50, 75, 90, 100]

def all_strokes(config, user):
    out = []
    for path in cfg_mod.list_sessions(config, user):
        for c, k in ch.segment(cfg_mod.load_session(path), config):
            if k == ch.MOVE: out.append(c[:, :2] - c[0, :2])
    return out

def main():
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml"); D = {}
    for u in USERS:
        S = all_strokes(config, u); reach = np.array([np.hypot(*s.T).max() for s in S]); pts = np.concatenate(S)
        hulls = {lv: MultiPoint(np.concatenate([s for s, r in zip(S, reach) if r <= np.percentile(reach, lv)])).convex_hull for lv in LEVELS}
        sub = pts[np.random.default_rng(0).choice(len(pts), min(len(pts), 60000), replace=False)]
        D[u] = {"S": S, "reach": reach, "hulls": hulls, "concave": shapely.concave_hull(MultiPoint(sub), ratio=.15), "sessions": len(cfg_mod.list_sessions(config, u))}
        print(f"{u}: {D[u]['sessions']} sessions, {len(S)} strokes, {len(pts)} points, median reach {np.median(reach):.0f}, max {reach.max():.0f}")
        for lv, h in hulls.items():
            c = 4 * np.pi * h.area / h.length ** 2; print(f"   convex {lv:3d}%: {h.area/1e3:8,.0f}k px²  compact {c:.2f}")
    rows = []
    for lv in LEVELS:
        a, b = D["user29"]["hulls"][lv], D["user20"]["hulls"][lv]
        rows.append({"level": lv, "user29_k": a.area / 1e3, "user20_k": b.area / 1e3, "IoU": a.intersection(b).area / a.union(b).area})
    t = pd.DataFrame(rows); t.to_csv(OUT / "whole_hulls.csv", index=False); print(t.round(2).to_string(index=False))
    fig, axs = plt.subplots(1, 3, figsize=(24, 8.5))
    for ax, u in zip(axs[:2], USERS):
        d = D[u]; idx = np.random.default_rng(1).choice(len(d["S"]), min(600, len(d["S"])), replace=False)
        for i in idx: ax.plot(*d["S"][i].T, color="grey", lw=.3, alpha=.4)
        for lv, c in zip(LEVELS, plt.cm.plasma(np.linspace(.15, .85, 4))):
            h = d["hulls"][lv]; ax.plot(*h.exterior.xy, color=c, lw=2, label=f"convex {lv}%: {h.area/1e3:,.0f}k px²")
        ax.fill(*d["concave"].exterior.xy, color=COL[u], alpha=.12)
        ax.plot(0, 0, "ro"); ax.invert_yaxis(); ax.set_aspect("equal"); ax.legend(loc="lower right", fontsize=9)
        ax.set_title(f"{u}: all {d['sessions']} sessions, {len(d['S']):,} strokes\n(grey = 600 sample strokes, shaded = concave hull)", color=COL[u])
    ax = axs[2]
    for u in USERS:
        for lv, ls in zip([50, 90], ["-", "--"]):
            h = D[u]["hulls"][lv]; ax.fill(*h.exterior.xy, color=COL[u], alpha=.12 if lv == 50 else .05); ax.plot(*h.exterior.xy, color=COL[u], lw=2.5, ls=ls, label=f"{u} convex {lv}%")
    ax.plot(0, 0, "ro"); ax.invert_yaxis(); ax.set_aspect("equal"); ax.legend(loc="lower right")
    ax.set_title("both users: 50% core (solid) and 90% hull (dashed)\n" + ", ".join(f"IoU {r.level}% = {r.IoU:.2f}" for r in t.itertuples()))
    for a in axs: a.set_xlabel("x offset (px)"); a.set_ylabel("y offset (px)")
    fig.suptitle("Whole data: convex hulls of every move stroke of every session, strokes moved to (0,0)", fontsize=14)
    fig.tight_layout(); fig.savefig(OUT / "whole_hulls_user29_user20.png", dpi=90); print("->", OUT / "whole_hulls_user29_user20.png")

if __name__ == "__main__":
    main()
