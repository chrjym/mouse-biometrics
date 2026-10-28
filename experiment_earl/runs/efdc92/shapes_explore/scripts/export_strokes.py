#!/usr/bin/env python3
"""Export every user29 stroke used in the shapes: one PNG each, a summary CSV and a raw-points CSV."""
import sys
from importlib import import_module
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import pairwise, cfg_mod, plot_mod, K
from shape_ways import align
ch = import_module("03_chunk_shapes")
OUT = Path("/home/tin/thesis-mouse-biometrics/experiment_earl/runs/efdc92/shapes_explore/strokes")

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml")
    band = int(config["dtw_band"] * config["resample_n"])
    legit, _, order = plot_mod.draw_users(config, config["seed"]); user = legit[0]
    raw = []   # same order as the library used by the shape scripts
    for f, n in order[user][:K]:
        chunks = ch.segment(cfg_mod.load_session(cfg_mod.ROOT / f / user / n), config)
        for j, (c, kind) in enumerate(chunks):
            if kind == ch.MOVE:
                p = ch.normalize(c, config["resample_n"])
                if p is not None: raw.append((n, j, c, p))
    lib = np.array([r[3] for r in raw])
    D = pairwise(lib, lib, band); np.fill_diagonal(D, np.inf)
    al = [align(p) for p in lib]
    rows, pts = [], []
    for i, (sess, j, c, p) in enumerate(raw):
        a = al[i]; sid = f"s{i + 1:03d}"
        bulge = float(a[:, 1].max()) if a is not None else np.nan
        rows.append({"stroke": sid, "session": sess, "chunk_in_session": j, "points": len(c),
                     "duration_s": round(c[-1, 2] - c[0, 2], 3), "length_px": round(ch.path_length(c), 1),
                     "start_x": c[0, 0], "start_y": c[0, 1], "end_x": c[-1, 0], "end_y": c[-1, 1],
                     "loop": a is None, "bulge": round(bulge, 3), 
                     "nearest_dtw": round(D[i].min(), 4), "file": f"{sid}.png"})
        pts += [{"stroke": sid, "t": t, "x": x, "y": y} for x, y, t in c]
        fig, ax = plt.subplots(1, 3, figsize=(11, 3.6))
        ax[0].plot(c[:, 0], c[:, 1], "-o", ms=3); ax[0].plot(*c[0, :2], "go"); ax[0].plot(*c[-1, :2], "rs")
        ax[0].invert_yaxis(); ax[0].set_aspect("equal", "datalim"); ax[0].set_title(f"screen px ({len(c)} pts, {rows[-1]['duration_s']} s)")
        ax[1].plot(*p.T); ax[1].plot(0, 0, "go"); ax[1].invert_yaxis(); ax[1].set_aspect("equal", "datalim"); ax[1].set_title("normalized: start (0,0), diag 1")
        if a is not None:
            ax[2].plot(*a.T, color="tab:purple"); ax[2].plot([0, 1], [0, 0], "k.", ms=8); ax[2].set_aspect("equal", "datalim")
            ax[2].set_title(f"aligned (0,0)->(1,0), bulge {bulge:.2f}")
        else:
            ax[2].text(.5, .5, "loop: ends near its start\n(not aligned, left out of shapes 2-4)", ha="center", va="center"); ax[2].axis("off")
        fig.suptitle(f"{sid}  {user} {sess} chunk {j}")
        fig.tight_layout(); fig.savefig(OUT / f"{sid}.png", dpi=80); plt.close(fig)
    pd.DataFrame(rows).to_csv(OUT.parent / "strokes.csv", index=False)
    pd.DataFrame(pts).to_csv(OUT.parent / "stroke_points.csv", index=False)
    # contact sheet
    n = len(raw); cols = 13; fig, axs = plt.subplots(int(np.ceil(n / cols)), cols, figsize=(cols * 1.4, np.ceil(n / cols) * 1.5))
    for i, ax in enumerate(axs.ravel()):
        ax.axis("off")
        if i < n:
            a = al[i]; q = a if a is not None else lib[i]
            ax.plot(*q.T, color="tab:purple" if a is not None else "tab:red", lw=1); ax.set_aspect("equal", "datalim")
            ax.set_title(f"s{i + 1:03d}", fontsize=7)
    fig.suptitle(f"{user}: all {n} strokes (purple = aligned, red = loop)"); fig.tight_layout()
    fig.savefig(OUT.parent / "all_strokes_user29.png", dpi=90); plt.close(fig)
    print(f"{n} strokes -> {OUT}/, strokes.csv, stroke_points.csv, all_strokes_user29.png")

if __name__ == "__main__":
    main()
