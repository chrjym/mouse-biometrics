#!/usr/bin/env python3
"""Ways to shape user29's strokes (0.04 / 4 sessions): direction-free alignment, chain, families, templates."""
import sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from chain_shape import pairwise, nn_chain, cfg_mod, match_mod, plot_mod, SENS, K
OUT = Path(__file__).parent
LOOP = 0.5   # chord shorter than this share of the box diagonal = loop

def align(p):
    """Rotate so start -> end points along +x, scale chord to 1, mirror so the bulge is above the chord."""
    v = p[-1] - p[0]; L = np.hypot(*v)
    if L < LOOP * np.hypot(*np.ptp(p, 0)): return None   # ends near its start: a loop, kept apart
    c, s = v / L; q = (p - p[0]) @ np.array([[c, -s], [s, c]]) / L
    return q * [1, -1] if q[np.abs(q[:, 1]).argmax(), 1] < 0 else q

def families(D, chain):
    runs, cur = [], [chain[0]]
    for a, b in zip(chain[:-1], chain[1:]):
        if D[a, b] <= SENS: cur.append(b)
        else: runs.append(cur); cur = [b]
    return [r for r in runs + [cur] if len(r) >= 3]

def main():
    config = cfg_mod.load_config(cfg_mod.ROOT / "runs/efdc92/1_9_0.04_4/config.yaml")
    band = int(config["dtw_band"] * config["resample_n"])
    legit, _, order = plot_mod.draw_users(config, config["seed"]); user = legit[0]
    lib = np.concatenate([match_mod.dataset_session(user, n, config, f).paths[0] for f, n in order[user][:K]])
    al = np.array([a for a in (align(p) for p in lib) if a is not None]); loops = [p for p in lib if align(p) is None]
    bulge = al[:, :, 1].max(1); where = al[np.arange(len(al)), al[:, :, 1].argmax(1), 0]
    D = pairwise(al, al, band); np.fill_diagonal(D, np.inf); chain = nn_chain(D); fams = families(D, chain)
    print(f"{user}: {len(loops)} loops set apart, {len(al)} aligned strokes, {len(fams)} families covering {sum(map(len, fams))}")
    print(f"  bulge median {np.median(bulge):.3f}, straight (<0.05) {np.mean(bulge < .05):.2f}, peak position median {np.median(where):.2f}")

    fig, ax = plt.subplots(2, 3, figsize=(19, 11)); ax = ax.ravel()
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
    end = np.zeros(2); cols = plt.cm.viridis(np.linspace(0, 1, len(chain)))
    for k, i in enumerate(chain):
        s = al[i] - al[i][0] + end; ax[3].plot(*s.T, color=cols[k], lw=.8); end = s[-1]
    ax[3].set_aspect("equal"); ax[3].set_title("4. nearest-neighbour chain of aligned strokes\n(now ordered by bend, not direction)")
    fc = plt.cm.tab10(np.arange(len(fams)) % 10)
    for r, fam in enumerate(fams[:10]):
        off = np.array([1.4 * (r % 5), -0.8 * (r // 5)])
        for i in fam: ax[4].plot(*(al[i] + off).T, color=fc[r], lw=.6, alpha=.6)
        ax[4].plot(*(al[fam].mean(0) + off).T, color="k", lw=1.6)
        ax[4].text(*(off + [.5, -.25]), f"n={len(fam)}", ha="center", fontsize=9)
    ax[4].set_aspect("equal"); ax[4].axis("off"); ax[4].set_title(f"5. families (chain cut at links > {SENS}), black = template")
    order_ = np.argsort(bulge)
    for k, i in enumerate(order_[:: max(1, len(order_) // 12)][:12]):
        off = np.array([1.4 * (k % 4), -0.9 * (k // 4)]); ax[5].plot(*(al[i] + off).T, color="tab:purple", lw=1.2)
        ax[5].text(*(off + [.5, -.15]), f"{bulge[i]:.2f}", ha="center", fontsize=8)
    ax[5].set_aspect("equal"); ax[5].axis("off"); ax[5].set_title("6. user29's shape alphabet: straight -> most curved")
    fig.tight_layout(); fig.savefig(OUT / "shape_ways_user29.png", dpi=100); print("  figure:", OUT / "shape_ways_user29.png")

if __name__ == "__main__":
    main()
