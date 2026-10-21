#!/usr/bin/env python3
"""Fair within- vs between-user comparison of user29 and user20: stroke Frechet, hull IoU and outline Frechet."""
import itertools, random, sys
from importlib import import_module
from pathlib import Path
import numpy as np, pandas as pd, shapely, numba, matplotlib
from shapely.geometry import MultiPoint
from shapely.geometry.polygon import orient
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, "/home/tin/thesis-mouse-biometrics/experiment_earl/src")
cfg_mod = import_module("00_config"); ch = import_module("03_chunk_shapes")
OUT = Path(__file__).parent; RUN = cfg_mod.ROOT / "runs/efdc92"
USERS = ["user29", "user20"]
N_SESSIONS = 8      # first sessions of each user's shuffled pool (seed 945)
N_STROKES = 15      # strokes drawn per session; sessions with fewer are skipped
SPACING = 0.01      # resample spacing, share of screen diagonal
STROKE_N = 32       # points per aligned stroke for stroke Frechet
RING_N = 120        # points per hull outline for outline Frechet
SEED = 945

def screen(config, user):
    """Screen size estimate: largest valid x and y over all of the user's sessions."""
    mx = my = 0
    for path in cfg_mod.list_sessions(config, user):
        df = cfg_mod.load_session(path); mx, my = max(mx, df.x.max()), max(my, df.y.max())
    return np.array([mx + 1, my + 1])

def resample(xy, step):
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    if arc[-1] == 0: return xy[:1]
    g = np.arange(0, arc[-1] + step / 2, step)
    return np.c_[np.interp(g, arc, xy[:, 0]), np.interp(g, arc, xy[:, 1])]

def align(p, n):
    """Arc-length resample to n points, start -> end on +x, chord 1, bend up; None for loops."""
    q = resample(p, max(np.hypot(*np.diff(p, axis=0).T).sum() / (n - 1), 1e-9))[:n]
    if len(q) < n: q = np.vstack([q, np.repeat(q[-1:], n - len(q), 0)])
    v = q[-1] - q[0]; L = np.hypot(*v)
    if L < .5 * np.hypot(*np.ptp(q, 0)): return None
    c, s = v / L; r = (q - q[0]) @ np.array([[c, -s], [s, c]]) / L
    return r * [1, -1] if r[np.abs(r[:, 1]).argmax(), 1] < 0 else r

@numba.njit(cache=True)
def frechet(a, b):
    n, m = a.shape[0], b.shape[0]; c = np.empty((n, m))
    for i in range(n):
        for j in range(m):
            d = np.sqrt((a[i, 0] - b[j, 0]) ** 2 + (a[i, 1] - b[j, 1]) ** 2)
            if i == 0 and j == 0: c[i, j] = d
            elif i == 0: c[i, j] = max(c[i, j - 1], d)
            elif j == 0: c[i, j] = max(c[i - 1, j], d)
            else: c[i, j] = max(d, min(c[i - 1, j], c[i - 1, j - 1], c[i, j - 1]))
    return c[n - 1, m - 1]

@numba.njit(cache=True)
def closed_frechet(a, b):
    best = np.inf
    for k in range(b.shape[0]):
        best = min(best, frechet(a, np.concatenate((b[k:], b[:k]))))   # every start point of b
    return best

def ring(poly):
    r = orient(poly).exterior; return np.array([r.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, RING_N, endpoint=False)])

def sessions(config, user, scr):
    out = []; rng = random.Random(f"{SEED}-{user}-strokes")
    for f, name in cfg_mod.session_pool(config, user, config["seed"])[:N_SESSIONS]:
        chunks = [c for c, k in ch.segment(cfg_mod.load_session(cfg_mod.ROOT / f / user / name), config) if k == ch.MOVE]
        strokes = [resample((c[:, :2] - c[0, :2]) / scr, SPACING) for c in chunks]   # (0,0) start, screen units, fixed spacing
        keep = [(s, a) for s in strokes if len(s) >= 3 and (a := align(s, STROKE_N)) is not None]
        if len(keep) < N_STROKES: print(f"  skip {user} {name}: {len(keep)} usable strokes"); continue
        keep = rng.sample(keep, N_STROKES); pts = np.concatenate([s for s, _ in keep])
        reach = np.array([np.hypot(*s.T).max() for s, _ in keep]); inner = [s for (s, _), r in zip(keep, reach) if r <= np.percentile(reach, 90)]
        out.append({"user": user, "session": name, "strokes": [s for s, _ in keep], "aligned": [a for _, a in keep],
                    "convex90": MultiPoint(np.concatenate(inner)).convex_hull, "concave": shapely.concave_hull(MultiPoint(pts), ratio=.15)})
    return out

def stroke_distance(A, B):
    """Symmetric mean over strokes of the Frechet distance to the nearest stroke of the other session."""
    D = np.array([[frechet(a, b) for b in B["aligned"]] for a in A["aligned"]])
    return (D.min(1).mean() + D.min(0).mean()) / 2

def auc(between, within):
    b, w = np.asarray(between)[:, None], np.asarray(within)[None]
    return float(((b > w) + .5 * (b == w)).mean())

def main():
    config = cfg_mod.load_config(RUN / "1_9_0.04_4/config.yaml")
    S = []
    for u in USERS:
        scr = screen(config, u); print(f"{u}: screen ~{scr[0]:.0f} x {scr[1]:.0f}"); S += sessions(config, u, scr)
    rows = []
    for A, B in itertools.combinations(S, 2):
        g = f"within {A['user']}" if A["user"] == B["user"] else "between"
        rows.append({"group": g, "a": f"{A['user']}/{A['session']}", "b": f"{B['user']}/{B['session']}",
                     "stroke_frechet": stroke_distance(A, B),
                     "convex90_IoU": A["convex90"].intersection(B["convex90"]).area / A["convex90"].union(B["convex90"]).area,
                     "concave_IoU": A["concave"].intersection(B["concave"]).area / A["concave"].union(B["concave"]).area,
                     "convex90_frechet": closed_frechet(ring(A["convex90"]), ring(B["convex90"])),
                     "concave_frechet": closed_frechet(ring(A["concave"]), ring(B["concave"]))})
    df = pd.DataFrame(rows); df.to_csv(OUT / "pairs.csv", index=False)
    metrics = [("stroke_frechet", "stroke Fréchet (aligned, chord = 1)", "dist"), ("convex90_IoU", "90% convex hull IoU", "sim"),
               ("concave_IoU", "concave hull IoU", "sim"), ("convex90_frechet", "90% convex outline Fréchet (screen units)", "dist"),
               ("concave_frechet", "concave outline Fréchet (screen units)", "dist")]
    within = df[df.group != "between"]; between = df[df.group == "between"]; summ = []
    for m, lab, kind in metrics:
        a = auc(between[m], within[m]) if kind == "dist" else auc(-between[m], -within[m])
        summ.append({"metric": m, **{g: df[df.group == g][m].median() for g in ["within user29", "within user20", "between"]}, "AUC_between_vs_within": a})
    summ = pd.DataFrame(summ); summ.to_csv(OUT / "summary.csv", index=False); print(df.group.value_counts().to_dict()); print(summ.round(3).to_string(index=False))
    # figure 1: metrics
    fig, axs = plt.subplots(1, 5, figsize=(24, 6)); order = ["within user29", "within user20", "between"]; cols = ["tab:blue", "tab:orange", "tab:purple"]
    for ax, (m, lab, kind), (_, s) in zip(axs, metrics, summ.iterrows()):
        for j, g in enumerate(order):
            v = df[df.group == g][m].values; ax.scatter(j + np.random.default_rng(j).uniform(-.15, .15, len(v)), v, s=14, color=cols[j], alpha=.7)
            ax.hlines(np.median(v), j - .3, j + .3, color="k", lw=2)
        ax.set_xticks(range(3), ["within\nuser29", "within\nuser20", "user29\nvs user20"])
        ax.set_title(f"{lab}\n{'higher' if kind == 'sim' else 'lower'} = more alike;  AUC {s.AUC_between_vs_within:.2f}", fontsize=10)
    fig.suptitle(f"Fair comparison: {N_STROKES} strokes per session, screen-scaled, resampled. AUC = chance that a between-user pair is less alike than a within-user pair (0.5 = no difference, 1 = fully distinct)")
    fig.tight_layout(); fig.savefig(OUT / "compare_fair_metrics.png", dpi=90); plt.close(fig)
    # figure 2: the fair shapes
    per = {u: [s for s in S if s["user"] == u] for u in USERS}; ncol = max(map(len, per.values()))
    fig, axs = plt.subplots(2, ncol, figsize=(3.2 * ncol, 7), sharex=True, sharey=True, squeeze=False)
    for r, u in enumerate(USERS):
        for c in range(ncol):
            ax = axs[r, c]; ax.set_aspect("equal")
            if c >= len(per[u]): ax.axis("off"); continue
            s = per[u][c]
            for st in s["strokes"]: ax.plot(*st.T, color="grey", lw=.6)
            ax.fill(*s["concave"].exterior.xy, color=cols[r], alpha=.2); ax.plot(*s["concave"].exterior.xy, color=cols[r], lw=1.5)
            ax.plot(*s["convex90"].exterior.xy, "k--", lw=1); ax.plot(0, 0, "ro", ms=4); ax.set_title(f"{u}\n{s['session'][-6:]}", fontsize=9, color=cols[r])
    axs[0, 0].invert_yaxis(); fig.suptitle(f"Shapes used: {N_STROKES} strokes per session, screen units (concave = colour, 90% convex = dashed)")
    fig.tight_layout(); fig.savefig(OUT / "compare_fair_shapes.png", dpi=90); print("->", OUT)

if __name__ == "__main__":
    main()
