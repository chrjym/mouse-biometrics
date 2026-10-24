#!/usr/bin/env python3
"""For one user: export strokes (first 4 pool sessions), put them at (0,0), concave / nested convex / per-stroke hulls.
Optional second argument (e.g. 0.5): cut each stroke into pieces of that many seconds; files get a _0.5s suffix."""
import sys
from importlib import import_module
from pathlib import Path
import numpy as np, pandas as pd, matplotlib, shapely
from shapely.geometry import MultiPoint, Polygon
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import cfg_mod, plot_mod, K
ch = import_module("03_chunk_shapes")
RUN = cfg_mod.ROOT / "runs/efdc92"

def strokes(user, config, piece=None):
    order = cfg_mod.session_pool(config, user, config["seed"]); rows, pts = [], []
    for f, n in order[:K]:
        for j, (c, kind) in enumerate(ch.segment(cfg_mod.load_session(cfg_mod.ROOT / f / user / n), config)):
            if kind != ch.MOVE or ch.normalize(c, config["resample_n"]) is None: continue
            parts = [c] if piece is None else [c[cut == k] for cut in [((c[:, 2] - c[0, 2]) // piece).astype(int)] for k in np.unique(cut)]
            for c in parts:
              if len(c) < 4 or np.ptp(c[:, :2], axis=0).max() == 0: continue
              sid = f"s{len(rows) + 1:03d}"
              rows.append({"stroke": sid, "session": n, "chunk_in_session": j, "points": len(c), "duration_s": round(c[-1, 2] - c[0, 2], 3),
                         "length_px": round(ch.path_length(c), 1), "start_x": c[0, 0], "start_y": c[0, 1], "end_x": c[-1, 0], "end_y": c[-1, 1]})
              pts += [{"stroke": sid, "t": t, "x": x, "y": y} for x, y, t in c]
    return pd.DataFrame(rows), pd.DataFrame(pts)

def base(ax, p, user):
    ax.plot(0, 0, "ro", ms=7); ax.invert_yaxis(); ax.set_aspect("equal"); ax.set_xlabel("x offset (px)"); ax.set_ylabel("y offset (px)")

def main(user, piece=None):
    config = cfg_mod.load_config(RUN / "1_9_0.04_4/config.yaml"); sfx = "" if piece is None else f"_{piece:g}s"
    out = RUN / ("shapes_explore" if user == "user29" else f"shapes_explore_{user}"); (out / f"strokes{sfx}").mkdir(parents=True, exist_ok=True)
    meta, p = strokes(user, config, piece); meta.to_csv(out / f"strokes{sfx}.csv", index=False); p.to_csv(out / f"stroke_points{sfx}.csv", index=False)
    what = "strokes" if piece is None else f"{piece:g} s pieces"
    p["ox"] = p.x - p.groupby("stroke").x.transform("first"); p["oy"] = p.y - p.groupby("stroke").y.transform("first")
    groups = list(p.groupby("stroke", sort=False)); n = len(groups); cmap = plt.cm.viridis
    for k, (s, g) in enumerate(groups):   # one PNG per stroke
        fig, ax = plt.subplots(figsize=(4, 4)); ax.plot(g.ox, g.oy, "-o", ms=3); base(ax, p, user)
        ax.set_title(f"{s} ({len(g)} pts, {meta.duration_s[k]} s)", fontsize=9); fig.tight_layout(); fig.savefig(out / f"strokes{sfx}" / f"{s}.png", dpi=70); plt.close(fig)
    # 1. all at origin
    fig, ax = plt.subplots(figsize=(10, 10))
    for k, (s, g) in enumerate(groups): c = cmap(k / n); ax.plot(g.ox, g.oy, color=c, lw=.8); ax.plot(g.ox.iloc[-1], g.oy.iloc[-1], ".", color=c)
    base(ax, p, user); ax.set_title(f"{user}: all {n} {what} moved to start at (0,0) (only shifted)"); fig.tight_layout()
    fig.savefig(out / f"all_strokes_origin_{user}{sfx}.png", dpi=100); plt.close(fig)
    cloud = MultiPoint(p[["ox", "oy"]].values); convex = cloud.convex_hull
    # 2. concave hulls at three ratios
    fig, axs = plt.subplots(1, 3, figsize=(21, 7.5))
    for ax, r, c in zip(axs, [.05, .15, .3], ["tab:green", "tab:blue", "tab:purple"]):
        h = shapely.concave_hull(cloud, ratio=r)
        for _, g in groups: ax.plot(g.ox, g.oy, color="grey", lw=.5, alpha=.5)
        ax.fill(*h.exterior.xy, color=c, alpha=.3); ax.plot(*h.exterior.xy, color=c, lw=2); ax.plot(*convex.exterior.xy, "k--", lw=.8)
        base(ax, p, user); ax.set_title(f"concave hull, ratio {r}\narea {h.area/1e3:,.0f}k px², perimeter {h.length:,.0f} px ({h.area/convex.area:.0%} of convex)")
    fig.suptitle(f"{user}: concave hull around all {n} {what} at (0,0) (dashed = convex hull)"); fig.tight_layout()
    fig.savefig(out / f"concave_hull_origin_{user}{sfx}.png", dpi=95); plt.close(fig)
    # 3. concave + nested convex hulls
    concave = shapely.concave_hull(cloud, ratio=.15); reach = np.hypot(p.ox, p.oy).groupby(p.stroke).max()
    levels = [50, 75, 90, 100]; cols = plt.cm.plasma(np.linspace(.15, .85, 4)); nested = []
    fig, axs = plt.subplots(1, 2, figsize=(19, 9))
    for ax in axs:
        for _, g in groups: ax.plot(g.ox, g.oy, color="grey", lw=.5, alpha=.45)
    axs[0].fill(*concave.exterior.xy, color="tab:blue", alpha=.25); axs[0].plot(*concave.exterior.xy, color="tab:blue", lw=2, label=f"concave hull 0.15 ({concave.area/1e3:,.0f}k px²)")
    for lv, c in zip(levels, cols):
        keep = reach[reach <= np.percentile(reach, lv)].index; h = MultiPoint(p[p.stroke.isin(keep)][["ox", "oy"]].values).convex_hull
        nested.append((lv, len(keep), h.area, concave.intersection(h).area / h.area))
        for ax in axs: ax.plot(*h.exterior.xy, color=c, lw=2, label=f"convex hull, {lv}% shortest strokes ({len(keep)}): {h.area/1e3:,.0f}k px²")
        if lv < 100: axs[1].fill(*h.exterior.xy, color=c, alpha=.12)
    for ax in axs: base(ax, p, user); ax.legend(loc="lower right", fontsize=8)
    axs[0].set_title("concave hull 0.15 with the convex hulls"); axs[1].set_title("nested convex hulls: shortest-reach strokes first")
    fig.suptitle(f"{user}: all {n} {what} at (0,0), concave and convex hulls (px)"); fig.tight_layout()
    fig.savefig(out / f"hulls_origin_{user}{sfx}.png", dpi=95); plt.close(fig)
    # 4. per-stroke convex hulls
    fig, ax = plt.subplots(figsize=(12, 11)); areas, polys = [], []
    for k, (s, g) in enumerate(groups):
        h = MultiPoint(g[["ox", "oy"]].values).convex_hull; c = cmap(k / n)
        if isinstance(h, Polygon): areas.append(h.area); polys.append(h); ax.fill(*h.exterior.xy, color=c, alpha=.12); ax.plot(*h.exterior.xy, color=c, lw=.7)
        ax.plot(g.ox, g.oy, color=c, lw=.5, alpha=.6)
    ax.plot(*concave.exterior.xy, color="tab:blue", lw=2.5, label=f"concave hull 0.15, all strokes ({concave.area/1e3:,.0f}k px²)")
    ax.plot(*convex.exterior.xy, "k--", lw=1.5, label=f"convex hull, all strokes ({convex.area/1e3:,.0f}k px²)")
    ax.plot([], [], color="grey", lw=4, alpha=.4, label=f"convex hull of each stroke ({len(areas)})"); base(ax, p, user); ax.legend(loc="lower right")
    ax.set_title(f"{user}: convex hull of every stroke, inside the concave and convex hulls of all strokes"); fig.tight_layout()
    fig.savefig(out / f"stroke_hulls_origin_{user}{sfx}.png", dpi=95); plt.close(fig)
    a = np.array(areas); u = shapely.union_all(polys)
    print(f"{user}: {n} strokes from sessions {', '.join(meta.session.unique())} ({meta.groupby('session', sort=False).size().tolist()})")
    print(f"  reach median {reach.median():.0f} px, max {reach.max():.0f}; points {len(p)}")
    print(f"  convex {convex.area/1e3:,.0f}k  concave0.15 {concave.area/1e3:,.0f}k")
    for lv, k, ar, ins in nested: print(f"  nested {lv}% ({k}): {ar/1e3:,.0f}k, {ins:.0%} inside concave")
    print(f"  per-stroke hull median {np.median(a)/1e3:.0f}k, p90 {np.percentile(a, 90)/1e3:.0f}k, max {a.max()/1e3:.0f}k; union {u.area/concave.area:.0%} of concave")
    print(f"  -> {out}")

if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else None)
