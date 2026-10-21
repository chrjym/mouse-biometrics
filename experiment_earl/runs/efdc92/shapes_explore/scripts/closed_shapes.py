#!/usr/bin/env python3
"""Four closed shapes for user29 (0.04 / 4 sessions): closed chain, convex hull, concave hull, envelope."""
import sys
from pathlib import Path
import numpy as np, matplotlib, shapely
from shapely.geometry import Polygon, MultiPoint
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import pairwise, nn_chain, cfg_mod, match_mod, plot_mod, K
from shape_ways import align
OUT = Path("/home/tin/thesis-mouse-biometrics/experiment_earl/runs/efdc92/shapes_explore")
ALPHA = 0.15    # concave hull ratio (0 = tightest, 1 = convex)
BAND = (10, 90) # envelope percentiles
BINS = 40

def envelope(al):
    """Per x-bin of the aligned strokes, the BAND percentiles of y; lower edge out, upper edge back."""
    pts = al.reshape(-1, 2); edges = np.linspace(0, 1, BINS + 1); xs, lo, hi = [], [], []
    for a, b in zip(edges[:-1], edges[1:]):
        y = pts[(pts[:, 0] >= a) & (pts[:, 0] < b), 1]
        if len(y) > 5: xs.append((a + b) / 2); lo.append(np.percentile(y, BAND[0])); hi.append(np.percentile(y, BAND[1]))
    xs = np.r_[0, xs, 1]; lo = np.r_[0, lo, 0]; hi = np.r_[0, hi, 0]
    return Polygon(np.r_[np.c_[xs, lo], np.c_[xs, hi][::-1]])

def describe(name, poly):
    print(f"  {name:14s} area {poly.area:7.3f}  perimeter {poly.length:7.3f}  valid {poly.is_valid}")

def fill(ax, poly, color):
    for g in getattr(poly, "geoms", [poly]):
        ax.fill(*g.exterior.xy, color=color, alpha=.35); ax.plot(*g.exterior.xy, color=color, lw=2)

def main():
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml")
    band = int(config["dtw_band"] * config["resample_n"])
    legit, _, order = plot_mod.draw_users(config, config["seed"]); user = legit[0]
    lib = np.concatenate([match_mod.dataset_session(user, n, config, f).paths[0] for f, n in order[user][:K]])
    D = pairwise(lib, lib, band); np.fill_diagonal(D, np.inf); chain = nn_chain(D)
    end, pts = np.zeros(2), []
    for i in chain: s = lib[i] + end; pts.append(s); end = s[-1]
    path = np.concatenate(pts)
    closed = Polygon(path).buffer(0)                      # 1. end joined to start
    al = np.array([a for a in (align(p) for p in lib) if a is not None]); cloud = MultiPoint(al.reshape(-1, 2))
    convex = cloud.convex_hull                            # 2.
    concave = shapely.concave_hull(cloud, ratio=ALPHA)    # 3.
    env = envelope(al)                                    # 4.
    print(f"{user}: {len(lib)} strokes, {len(al)} aligned ({len(lib) - len(al)} loops left out)")
    for n, p in [("1 closed chain", closed), ("2 convex hull", convex), ("3 concave hull", concave), ("4 envelope", env)]: describe(n, p)

    fig, ax = plt.subplots(1, 4, figsize=(22, 6.5))
    cols = plt.cm.viridis(np.linspace(0, 1, len(pts)))
    for s, c in zip(pts, cols): ax[0].plot(*s.T, color=c, lw=.7)
    ax[0].plot(*np.array([path[-1], path[0]]).T, color="red", lw=2, ls="--", label="closing line (artificial)")
    fill(ax[0], closed, "tab:blue"); ax[0].invert_yaxis(); ax[0].legend(loc="lower left")
    ax[0].set_title(f"1. chain closed end -> start\narea {closed.area:.1f}, perimeter {closed.length:.1f} (stroke units)")
    for k, (poly, t, c) in enumerate([(convex, "2. convex hull", "tab:orange"), (concave, f"3. concave hull (ratio {ALPHA})", "tab:green"),
                                      (env, f"4. envelope ({BAND[0]}th-{BAND[1]}th percentile)", "tab:purple")], 1):
        for a in al: ax[k].plot(*a.T, color="grey", lw=.4, alpha=.4)
        fill(ax[k], poly, c); ax[k].plot([0, 1], [0, 0], "k.", ms=10)
        ax[k].set_title(f"{t}\narea {poly.area:.3f}, perimeter {poly.length:.2f}")
        ax[k].set_xlim(-.9, 2); ax[k].set_ylim(-.5, 1.5)
    if True:
        m = al.mean(0); ax[3].plot(*m.T, color="red", lw=2, label="mean stroke"); ax[3].legend()
    for a in ax: a.set_aspect("equal")
    fig.suptitle(f"{user}: closed shapes from {len(lib)} strokes (4 sessions, sensitivity 0.04). Panels 2-4: strokes turned to run (0,0) -> (1,0), bend up", y=1.0)
    fig.tight_layout(); fig.savefig(OUT / "closed_shapes_user29.png", dpi=100, bbox_inches="tight"); print("  figure:", OUT / "closed_shapes_user29.png")

if __name__ == "__main__":
    main()
