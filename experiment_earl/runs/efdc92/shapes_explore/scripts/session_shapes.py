#!/usr/bin/env python3
"""One panel per session: strokes at (0,0), 90% convex hull and concave hull (r = 0.15), user29 and user20."""
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd, shapely
from shapely.geometry import MultiPoint
R = Path(__file__).resolve().parents[2]; OUT = R / "shapes_explore"
USERS = {"user29": "shapes_explore", "user20": "shapes_explore_user20"}; COL = {"user29": "tab:blue", "user20": "tab:orange"}

def load(folder):
    p = pd.read_csv(R / folder / "stroke_points.csv").merge(pd.read_csv(R / folder / "strokes.csv")[["stroke", "session"]])
    p["ox"] = p.x - p.groupby("stroke").x.transform("first"); p["oy"] = p.y - p.groupby("stroke").y.transform("first"); return p

def hulls(p):
    out = []
    for s, g in p.groupby("session", sort=False):
        reach = np.hypot(g.ox, g.oy).groupby(g.stroke).max(); keep = reach[reach <= np.percentile(reach, 90)].index
        out.append({"session": s, "n": g.stroke.nunique(), "convex90": MultiPoint(g[g.stroke.isin(keep)][["ox", "oy"]].values).convex_hull,
                    "concave": shapely.concave_hull(MultiPoint(g[["ox", "oy"]].values), ratio=.15)})
    return out


def main():
    fig, axs = plt.subplots(2, 4, figsize=(22, 11.5), sharex=True, sharey=True)
    for r, (u, folder) in enumerate(USERS.items()):
        p = load(folder)
        for c, h in enumerate(hulls(p)):
            ax = axs[r, c]; g = p[p.session == h["session"]]
            for _, s in g.groupby("stroke"): ax.plot(s.ox, s.oy, color="grey", lw=.5, alpha=.6)
            ax.fill(*h["concave"].exterior.xy, color=COL[u], alpha=.15); ax.plot(*h["concave"].exterior.xy, color=COL[u], lw=1.8, label=f"concave hull 0.15: {h['concave'].area/1e3:,.0f}k px²")
            ax.plot(*h["convex90"].exterior.xy, "k--", lw=1.3, label=f"90% convex hull: {h['convex90'].area/1e3:,.0f}k px²")
            ax.plot(0, 0, "ro", ms=5); ax.set_aspect("equal"); ax.legend(loc="lower right", fontsize=8)
            ax.set_title(f"{u}  {h['session']}\n{h['n']} strokes", color=COL[u])
    axs[0, 0].invert_yaxis()
    for ax in axs[1]: ax.set_xlabel("x offset (px)")
    for ax in axs[:, 0]: ax.set_ylabel("y offset (px)")
    fig.suptitle("Shape of each session: strokes moved to (0,0) (grey), concave hull (colour), 90% convex hull (dashed); same scale in every panel", fontsize=13)
    fig.tight_layout(); fig.savefig(OUT / "session_shapes_user29_user20.png", dpi=90); print("->", OUT / "session_shapes_user29_user20.png")

if __name__ == "__main__":
    main()
