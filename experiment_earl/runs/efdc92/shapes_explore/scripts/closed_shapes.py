#!/usr/bin/env python3
"""Two closed shapes for user29 (0.04 / 4 sessions): convex hull, then concave hull."""
import sys
from pathlib import Path
import numpy as np, matplotlib, shapely
from shapely.geometry import MultiPoint
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import cfg_mod, match_mod, plot_mod, K
from shape_ways import align
OUT = Path("/home/tin/thesis-mouse-biometrics/experiment_earl/runs/efdc92/shapes_explore")
ALPHA = 0.15    # concave hull ratio (0 = tightest, 1 = convex)

def describe(name, poly):
    print(f"  {name:14s} area {poly.area:7.3f}  perimeter {poly.length:7.3f}  valid {poly.is_valid}")

def fill(ax, poly, color):
    for g in getattr(poly, "geoms", [poly]):
        ax.fill(*g.exterior.xy, color=color, alpha=.35); ax.plot(*g.exterior.xy, color=color, lw=2)

def main():
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml")
    legit, _, order = plot_mod.draw_users(config, config["seed"]); user = legit[0]
    lib = np.concatenate([match_mod.dataset_session(user, n, config, f).paths[0] for f, n in order[user][:K]])
    al = np.array([a for a in (align(p) for p in lib) if a is not None]); cloud = MultiPoint(al.reshape(-1, 2))
    convex = cloud.convex_hull                            # 1.
    concave = shapely.concave_hull(cloud, ratio=ALPHA)    # 2.
    print(f"{user}: {len(lib)} strokes, {len(al)} aligned ({len(lib) - len(al)} loops left out)")
    for n, p in [("1 convex hull", convex), ("2 concave hull", concave)]: describe(n, p)

    fig, ax = plt.subplots(1, 2, figsize=(12, 6.5))
    for k, (poly, t, c) in enumerate([(convex, "1. convex hull", "tab:orange"), (concave, f"2. concave hull (ratio {ALPHA})", "tab:green")]):
        for a in al: ax[k].plot(*a.T, color="grey", lw=.4, alpha=.4)
        fill(ax[k], poly, c); ax[k].plot([0, 1], [0, 0], "k.", ms=10)
        ax[k].set_title(f"{t}\narea {poly.area:.3f}, perimeter {poly.length:.2f}")
        ax[k].set_xlim(-.9, 2); ax[k].set_ylim(-.5, 1.5)
    for a in ax: a.set_aspect("equal")
    fig.suptitle(f"{user}: closed shapes from {len(lib)} strokes (4 sessions, sensitivity 0.04). Strokes turned to run (0,0) -> (1,0), bend up", y=1.0)
    fig.tight_layout(); fig.savefig(OUT / "closed_shapes_user29.png", dpi=100, bbox_inches="tight"); print("  figure:", OUT / "closed_shapes_user29.png")

if __name__ == "__main__":
    main()
