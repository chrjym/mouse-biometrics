#!/usr/bin/env python3
"""Ways to shape user29's strokes (0.04 / 4 sessions): direction-free alignment, bend map, shape alphabet."""
import sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import cfg_mod, match_mod, plot_mod, K
OUT = Path(__file__).parent
LOOP = 0.5   # chord shorter than this share of the box diagonal = loop

def align(p):
    """Rotate so start -> end points along +x, scale chord to 1, mirror so the bulge is above the chord."""
    v = p[-1] - p[0]; L = np.hypot(*v)
    if L < LOOP * np.hypot(*np.ptp(p, 0)): return None   # ends near its start: a loop, kept apart
    c, s = v / L; q = (p - p[0]) @ np.array([[c, -s], [s, c]]) / L
    return q * [1, -1] if q[np.abs(q[:, 1]).argmax(), 1] < 0 else q

def main():
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml")
    legit, _, order = plot_mod.draw_users(config, config["seed"]); user = legit[0]
    lib = np.concatenate([match_mod.dataset_session(user, n, config, f).paths[0] for f, n in order[user][:K]])
    al = np.array([a for a in (align(p) for p in lib) if a is not None]); loops = [p for p in lib if align(p) is None]
    bulge = al[:, :, 1].max(1); where = al[np.arange(len(al)), al[:, :, 1].argmax(1), 0]
    print(f"{user}: {len(loops)} loops set apart, {len(al)} aligned strokes")
    print(f"  bulge median {np.median(bulge):.3f}, straight (<0.05) {np.mean(bulge < .05):.2f}, peak position median {np.median(where):.2f}")

    fig, ax = plt.subplots(2, 2, figsize=(13, 11)); ax = ax.ravel()
    for p in lib: ax[0].plot(*p.T, color="grey", lw=.5, alpha=.5)
    ax[0].set_title("1. raw normalized strokes (direction still in)"); ax[0].invert_yaxis(); ax[0].set_aspect("equal")
    for p in al: ax[1].plot(*p.T, color="tab:blue", lw=.5, alpha=.3)
    m, sd = al.mean(0), al[:, :, 1].std(0)
    ax[1].fill_between(m[:, 0], m[:, 1] - sd, m[:, 1] + sd, color="orange", alpha=.35, label="mean ± 1 sd")
    ax[1].plot(*m.T, color="red", lw=2.5, label="mean stroke"); ax[1].legend(); ax[1].set_aspect("equal")
    ax[1].set_title("2. aligned: start->end on x-axis, chord = 1, bulge up\n(direction removed, curvature habit remains)")
    h = ax[2].hist2d(bulge, where, bins=[25, 20], range=[[0, .6], [-.2, 1.2]], cmap="viridis")
    ax[2].set_xlabel("bulge (max height / chord)"); ax[2].set_ylabel("where the bulge peaks (0 = start, 1 = end)")
    ax[2].set_title("3. two-number shape: how much it bends, and where")
    order_ = np.argsort(bulge)
    for k, i in enumerate(order_[:: max(1, len(order_) // 12)][:12]):
        off = np.array([1.4 * (k % 4), -0.9 * (k // 4)]); ax[3].plot(*(al[i] + off).T, color="tab:purple", lw=1.2)
        ax[3].text(*(off + [.5, -.15]), f"{bulge[i]:.2f}", ha="center", fontsize=8)
    ax[3].set_aspect("equal"); ax[3].axis("off"); ax[3].set_title("4. user29's shape alphabet: straight -> most curved")
    fig.tight_layout(); fig.savefig(OUT / "shape_ways_user29.png", dpi=100); print("  figure:", OUT / "shape_ways_user29.png")

if __name__ == "__main__":
    main()
