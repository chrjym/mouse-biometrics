#!/usr/bin/env python3
"""Side-by-side, explainable shape description of user29 and user20 (first 4 sessions, strokes at (0,0))."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, shapely, matplotlib
from shapely.geometry import MultiPoint
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = Path(__file__).resolve().parents[1]; OUT = Path(__file__).parent
sys.path.insert(0, str(R / "shapes_explore/scripts"))
from shape_ways import align
USERS = {"user29": "shapes_explore", "user20": "shapes_explore_user20"}; COL = {"user29": "tab:blue", "user20": "tab:orange"}

def resample(xy, n=64):
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    if arc[-1] == 0: return None
    g = np.linspace(0, arc[-1], n); return np.c_[np.interp(g, arc, xy[:, 0]), np.interp(g, arc, xy[:, 1])]

def describe(folder):
    p = pd.read_csv(R / folder / "stroke_points.csv"); strokes = []
    for s, g in p.groupby("stroke", sort=False):
        xy = g[["x", "y"]].values.astype(float); xy -= xy[0]; q = resample(xy)
        if q is None: continue
        chord = np.hypot(*q[-1]); length = np.hypot(*np.diff(q, axis=0).T).sum()
        a = align(q / max(np.hypot(*np.ptp(q, 0)), 1e-9))
        strokes.append({"xy": xy, "q": q, "reach": np.hypot(*xy.T).max(), "length": length, "straight": chord / length,
                        "angle": np.degrees(np.arctan2(-q[-1, 1], q[-1, 0])) % 360, "aligned": a,
                        "bulge": a[:, 1].max() if a is not None else np.nan, "peak": a[a[:, 1].argmax(), 0] if a is not None else np.nan,
                        "duration": g.t.iloc[-1] - g.t.iloc[0]})
    pts = np.concatenate([s["xy"] for s in strokes]); reach = np.array([s["reach"] for s in strokes])
    inner = np.concatenate([s["xy"] for s in strokes if s["reach"] <= np.percentile(reach, 90)])
    hull90 = MultiPoint(inner).convex_hull; concave = shapely.concave_hull(MultiPoint(pts), ratio=.15)
    cov = np.cov(inner.T); ev, evec = np.linalg.eigh(cov)
    return strokes, {"hull90": hull90, "concave": concave, "elong": np.sqrt(ev[1] / ev[0]),
                     "main_dir": np.degrees(np.arctan2(-evec[1, 1], evec[0, 1])) % 180}

def main():
    D = {u: describe(f) for u, f in USERS.items()}; rows = []
    for u, (S, H) in D.items():
        al = [s for s in S if s["aligned"] is not None]; c = H["concave"]
        rows.append({"user": u, "strokes": len(S),
            "median reach (px)": np.median([s["reach"] for s in S]), "median path length (px)": np.median([s["length"] for s in S]),
            "median duration (s)": np.median([s["duration"] for s in S]),
            "straightness (chord / path, 1 = straight)": np.median([s["straight"] for s in S]),
            "median bend (bulge / chord)": np.median([s["bulge"] for s in al]), "bend peaks at (0 start, 1 end)": np.median([s["peak"] for s in al]),
            "loops (end near start)": f"{(len(S) - len(al)) / len(S):.0%}",
            "90% convex hull area (k px²)": H["hull90"].area / 1e3, "concave hull area (k px²)": c.area / 1e3,
            "concave compactness 4πA/P² (1 = circle)": 4 * np.pi * c.area / c.length ** 2,
            "elongation (long / short axis)": H["elong"], "main axis (deg, 0 = horizontal)": H["main_dir"]})
    t = pd.DataFrame(rows).set_index("user").T; t.to_csv(OUT / "descriptors.csv"); print(t.to_string(float_format=lambda v: f"{v:.2f}"))
    fig = plt.figure(figsize=(22, 13)); g = fig.add_gridspec(2, 4)
    # 1 directions
    for k, u in enumerate(D):
        ax = fig.add_subplot(g[0, k], projection="polar"); ang = np.radians([s["angle"] for s in D[u][0]])
        ax.hist(ang, bins=16, color=COL[u], alpha=.75); ax.set_title(f"1. {u}: direction of strokes\n(0° = right, 90° = up)", color=COL[u])
    # 2 hulls overlay
    ax = fig.add_subplot(g[0, 2])
    for u, (S, H) in D.items():
        ax.fill(*H["concave"].exterior.xy, color=COL[u], alpha=.15); ax.plot(*H["concave"].exterior.xy, color=COL[u], lw=1.5, label=f"{u} concave hull")
        ax.plot(*H["hull90"].exterior.xy, color=COL[u], lw=2.5, ls="--", label=f"{u} 90% convex hull")
    ax.plot(0, 0, "ro"); ax.invert_yaxis(); ax.set_aspect("equal"); ax.legend(fontsize=8, loc="lower right"); ax.set_title("2. where strokes reach (hulls, px)")
    # 3 reach / length distributions
    ax = fig.add_subplot(g[0, 3])
    for u, (S, _) in D.items(): ax.hist([s["reach"] for s in S], bins=np.arange(0, 1900, 75), color=COL[u], alpha=.55, density=True, label=u)
    ax.set_xlabel("reach of a stroke (px)"); ax.set_ylabel("share of strokes"); ax.legend(); ax.set_title("3. how far strokes go")
    # 4 mean aligned stroke + envelope
    ax = fig.add_subplot(g[1, 0])
    for u, (S, _) in D.items():
        A = np.array([s["aligned"] for s in S if s["aligned"] is not None]); m = A.mean(0)
        lo, hi = np.percentile(A[:, :, 1], 25, 0), np.percentile(A[:, :, 1], 75, 0)
        ax.fill_between(m[:, 0], lo, hi, color=COL[u], alpha=.2); ax.plot(*m.T, color=COL[u], lw=2.5, label=f"{u} average stroke (band = middle 50%)")
    ax.plot([0, 1], [0, 0], "k.", ms=10); ax.set_aspect("equal"); ax.legend(fontsize=8); ax.set_title("4. how a stroke bends\n(turned to run (0,0) -> (1,0), bend up)")
    # 5 bend vs peak
    ax = fig.add_subplot(g[1, 1])
    for u, (S, _) in D.items():
        ax.scatter([s["peak"] for s in S], [s["bulge"] for s in S], s=12, color=COL[u], alpha=.5, label=u)
    ax.set_xlim(-.1, 1.1); ax.set_ylim(0, .8); ax.set_xlabel("where the bend peaks (0 = start, 1 = end)"); ax.set_ylabel("bend (height / chord)"); ax.legend(); ax.set_title("5. bend amount and position, one dot per stroke")
    # 6 straightness
    ax = fig.add_subplot(g[1, 2])
    for u, (S, _) in D.items(): ax.hist([s["straight"] for s in S], bins=np.linspace(0, 1, 26), color=COL[u], alpha=.55, density=True, label=u)
    ax.set_xlabel("straightness (1 = perfectly straight)"); ax.legend(); ax.set_title("6. how straight strokes are")
    # 7 table
    ax = fig.add_subplot(g[1, 3]); ax.axis("off")
    cell = [[k] + [f"{v:.2f}" if isinstance(v, float) else str(v) for v in t.loc[k]] for k in t.index]
    tb = ax.table(cellText=cell, colLabels=["", "user29", "user20"], loc="center", colWidths=[.62, .19, .19]); tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.45)
    ax.set_title("7. numbers")
    fig.suptitle("user29 vs user20: shapes described side by side (first 4 sessions each, strokes moved to (0,0))", fontsize=14)
    fig.tight_layout(); fig.savefig(OUT / "explain_user29_user20.png", dpi=90); print("->", OUT / "explain_user29_user20.png")

if __name__ == "__main__":
    main()
