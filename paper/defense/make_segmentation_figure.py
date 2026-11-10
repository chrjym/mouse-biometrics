"""Raw session -> strokes -> normalized strokes, from the notebook's own stroke export (run a6e6f7)."""
import sys
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
root, out = Path(sys.argv[1]), Path(sys.argv[2])
user, sess = "user29", "session_0136325499"
raw = pd.read_csv(root / "datasets/balabit/users" / user / sess)
raw = raw[(raw.x != 65535) & (raw.y != 65535)]
pts = pd.read_csv(root / "runs/a6e6f7/strokes" / user / f"{sess}_points.csv")
meta = pd.read_csv(root / "runs/a6e6f7/strokes" / user / f"{sess}.csv")
fig, ax = plt.subplots(1, 3, figsize=(16, 5.2))
ax[0].plot(raw.x, raw.y, lw=0.5, color="0.35")
clk = raw[raw.state == "Pressed"]
ax[0].scatter(clk.x, clk.y, s=8, color="crimson", zorder=3, label=f"clicks ({len(clk)})")
ax[0].set_title(f"(a) Raw session: {len(raw):,} records")
ax[0].legend(loc="lower right")
cmap = plt.get_cmap("tab20")
s = pts.dropna(subset=["stroke"])
for i, (k, g) in enumerate(s.groupby("stroke")):
    ax[1].plot(g.x, g.y, lw=1, color=cmap(i % 20))
ax[1].set_title(f"(b) Cut at pauses > 0.5 s and clicks: {s.stroke.nunique()} strokes (>= 10 points)")
n = 0
for k, g in s.groupby("stroke"):
    xy = g[["x", "y"]].to_numpy(float); xy -= xy[0]
    d = np.hypot(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]))
    if d == 0: continue
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    grid = np.linspace(0, arc[-1], 64)
    r = np.c_[np.interp(grid, arc, xy[:, 0]), np.interp(grid, arc, xy[:, 1])] / d
    ax[2].plot(r[:, 0], r[:, 1], lw=0.7, alpha=0.6, color="tab:blue"); n += 1
ax[2].scatter([0], [0], color="k", zorder=3, s=15)
ax[2].set_title(f"(c) {n} strokes moved to (0, 0), scaled, 64 points each")
for a in ax[:2]:
    a.invert_yaxis(); a.set_xlabel("x (px)"); a.set_ylabel("y (px)"); a.set_aspect("equal", "datalim")
ax[2].invert_yaxis(); ax[2].set_aspect("equal", "datalim"); ax[2].set_xlabel("x / diagonal"); ax[2].set_ylabel("y / diagonal")
fig.suptitle(f"Balabit {user}, {sess}: raw data to strokes")
fig.tight_layout(); fig.savefig(out, dpi=150)
print(len(raw), s.stroke.nunique(), len(meta), meta.kind.value_counts().to_dict(), n, int(meta.compared.sum()))
