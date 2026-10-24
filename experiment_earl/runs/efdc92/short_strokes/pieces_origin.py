#!/usr/bin/env python3
"""All 0.5 s pieces of the first 4 sessions at (0,0), one panel per user, plus a check of piece durations."""
import sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).parent))
from short_strokes import ch, cfg_mod, K, RUN, OUT, USERS, PIECE, MIN_PTS

def pieces_t(user, session, folder, config):
    """Same cut as short_strokes.pieces, but keeps time so durations can be checked."""
    out = []
    for c, kind in ch.segment(cfg_mod.load_session(cfg_mod.ROOT / folder / user / session), config):
        if kind != ch.MOVE or ch.normalize(c, config["resample_n"]) is None: continue
        cut = ((c[:, 2] - c[0, 2]) // PIECE).astype(int)
        for k in np.unique(cut):
            q = c[cut == k]
            if len(q) >= MIN_PTS and np.ptp(q[:, :2], axis=0).max() > 0: out.append(q - [q[0, 0], q[0, 1], q[0, 2]])
    return out

config = cfg_mod.load_config(RUN / "1_9_0.04_4/config.yaml")
data = {u: [p for f, n in cfg_mod.session_pool(config, u, config["seed"])[:K] for p in pieces_t(u, n, f, config)] for u in USERS}
lim = max(np.abs(np.vstack(ps)[:, :2]).max() for ps in data.values()) * 1.05
fig, axs = plt.subplots(1, 2, figsize=(18, 9))
for ax, u in zip(axs, USERS):
    ps = data[u]; d = np.array([p[-1, 2] for p in ps]); cmap = plt.cm.viridis
    for k, p in enumerate(ps): ax.plot(p[:, 0], p[:, 1], color=cmap(k / len(ps)), lw=.6)
    ax.plot(0, 0, "ro", ms=7); ax.set_xlim(-lim, lim); ax.set_ylim(lim, -lim); ax.set_aspect("equal")
    ax.set_xlabel("x offset (px)"); ax.set_ylabel("y offset (px)")
    ax.set_title(f"{u}: {len(ps)} pieces of ≤ {PIECE} s at (0,0) (only shifted)\nduration median {np.median(d):.2f} s, max {d.max():.2f} s")
    print(f"{u}: {len(ps)} pieces, duration min {d.min():.3f} median {np.median(d):.3f} max {d.max():.3f} s, all <= {PIECE}: {bool((d <= PIECE).all())}")
fig.suptitle(f"All 0.5 s pieces of the first {K} sessions, moved to start at (0,0)"); fig.tight_layout()
fig.savefig(OUT / "all_pieces_origin_user29_user20.png", dpi=95); print(OUT / "all_pieces_origin_user29_user20.png")
