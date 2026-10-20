#!/usr/bin/env python3
"""Draw what 19 does: for a genuine, a typical impostor and the top impostor claim, each stroke next to its nearest stroke in the claimed user's library and in every other person's; plus genuine vs impostor scores per split, in runs/<hash>/cohort/plots/."""

import argparse
from importlib import import_module
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit, prange

cfg_mod = import_module("00_config")
match_mod = import_module("04_match_shapes")
cohort_mod = import_module("19_cohort_score")

ROOT = Path(__file__).resolve().parents[1]
_dtw_cost = cohort_mod._dtw_cost
CLAIMED, CLOSER, FARTHER, QUERY = "#1f5f8b", "#c0392b", "#9a9a9a", "#111111"


@njit(parallel=True, cache=True)
def nearest_index(queries, library, band, cap):
    """Per query path: the lowest DTW cost to any library path (capped) and that path's index (-1 if none under cap)."""
    n = queries.shape[1]
    best = np.full(queries.shape[0], cap)
    index = np.full(queries.shape[0], -1)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            cost = _dtw_cost(queries[q], library[k], band, best[q], prev, cur)
            if cost < best[q]:
                best[q], index[q] = cost, k
    return best, index


def strokes_of(session) -> list[tuple[int, np.ndarray]]:
    """(kind, path) per stroke, kinds in 19's fixed order, so position i matches 19's per-stroke arrays."""
    return [(kind, path) for kind in sorted(session.paths) for path in session.paths[kind]]


def nearest_stroke(path: np.ndarray, kind: int, library: dict, config: dict, cap: float) -> tuple[float, np.ndarray | None]:
    """Cost per point and the nearest same-kind stroke of a library (None when nothing is under the cap)."""
    n = config["resample_n"]
    if kind not in library or not len(library[kind]):
        return cap, None
    cost, index = nearest_index(path[None], library[kind], int(round(config["dtw_band"] * n)), cap * n)
    return float(cost[0] / n), library[kind][index[0]] if index[0] >= 0 else None


def draw_path(ax, path: np.ndarray | None, colour: str, width: float, style: str = "-") -> None:
    if path is not None:
        ax.plot(path[:, 0], path[:, 1], style, color=colour, linewidth=width)
        ax.plot(path[0, 0], path[0, 1], "o", color=colour, markersize=2.5)


def plot_claim(claim: pd.Series, users: list[str], libraries: dict, config: dict, cap: float, n_strokes: int,
               path: Path, why: str) -> None:
    """Rows = strokes of the session spread over its rank range; column 1 = the claimed user's nearest stroke, the
    others = each other person's nearest stroke (red = closer than the claimed user's, counts against the claim)."""
    session = match_mod.dataset_session(claim.author, claim.session, config)
    strokes = strokes_of(session)
    others = [w for w in users if w not in (claim.claimed, claim.author)]
    own = cohort_mod.library_nearest(session, *libraries[("profile", claim.claimed)], config, cap)
    rest = np.array([cohort_mod.library_nearest(session, *libraries[("background", w)], config, cap) for w in others])
    rank = ((rest > own).sum(axis=0) + 0.5 * (rest == own).sum(axis=0)) / len(others)
    picks = np.argsort(rank, kind="stable")[np.linspace(0, len(rank) - 1, min(n_strokes, len(rank))).round().astype(int)][::-1]

    cols = 1 + len(others)
    fig = plt.figure(figsize=(1.45 * cols + 1.2, 1.45 * len(picks) + 2.6), layout="constrained")
    grid = fig.add_gridspec(len(picks) + 1, cols, height_ratios=[1] * len(picks) + [1.4])
    for row, i in enumerate(picks):
        kind, query = strokes[i]
        cells = [(claim.claimed, libraries[("profile", claim.claimed)][1], True)]
        cells += [(w, libraries[("background", w)][1], False) for w in others]
        for col, (user, library, is_claimed) in enumerate(cells):
            ax = fig.add_subplot(grid[row, col])
            cost, match = nearest_stroke(query, kind, library, config, cap)
            if is_claimed:
                colour, verdict = CLAIMED, "claimed"
            else:
                colour, verdict = (CLOSER, "closer") if cost < own[i] else (FARTHER, "farther") if cost > own[i] else (FARTHER, "tie")
            draw_path(ax, query, QUERY, 1.6)
            draw_path(ax, match, colour, 1.4, "--")
            ax.set_title(f"{user}\n{cost:.3f} {verdict}", fontsize=7, color=colour if colour != FARTHER else "#555555")
            ax.set_aspect("equal", adjustable="datalim")
            ax.invert_yaxis()
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color(colour if is_claimed else "#dddddd")
                spine.set_linewidth(2 if is_claimed else 0.8)
            if col == 0:
                ax.set_ylabel(f"stroke {i}\nrank {rank[i]:.2f}", fontsize=8)
    hist = fig.add_subplot(grid[-1, :])
    hist.hist(rank, bins=np.linspace(0, 1, 21), color=CLAIMED, alpha=0.75, edgecolor="white")
    hist.axvline(rank.mean(), color=QUERY, linewidth=2, label=f"session score = mean rank = {rank.mean():.3f}")
    hist.axvline(0.5, color=FARTHER, linewidth=1, linestyle=":", label="0.5 = no evidence")
    hist.set(xlim=(0, 1), xlabel=f"stroke rank = share of the {len(others)} other people whose nearest stroke is farther "
                                 f"than {claim.claimed}'s (ties ½)", ylabel="strokes")
    hist.legend(fontsize=8, loc="upper left")
    kind = "genuine" if claim.genuine else f"impostor ({claim.author} claiming to be {claim.claimed})"
    fig.suptitle(f"{kind}: {claim.author}/{claim.session}, {claim.sessions} sessions per user "
                 f"(libraries of {claim.library_strokes} strokes); {why}\n"
                 f"black = the session's stroke, dashed = nearest stroke in that library, number = DTW cost per point; "
                 f"blue = claimed user, red = closer than the claimed user (against), grey = farther (for)",
                 fontsize=9)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    if not np.isclose(rank.mean(), claim.cohort):
        print(f"  warning: recomputed score {rank.mean():.4f} differs from sessions.csv {claim.cohort:.4f}")


def plot_scores(sessions: pd.DataFrame, cells: pd.DataFrame, best: pd.DataFrame, users: list[str], path: Path,
                title: str) -> None:
    """Per split at its chosen sessions: every claim's cohort score, genuine above, impostor below, with 19's chosen
    threshold; claims right of the line are accepted."""
    splits = list(best[["n_legitimate", "n_impostor"]].itertuples(index=False, name=None))
    cols = 3
    rows = -(-len(splits) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 2.4 * rows), squeeze=False, sharex=True,
                             layout="constrained")
    rng = np.random.default_rng(0)
    for ax, (legit_n, impostor_n) in zip(axes.flat, splits):
        k = int(best[(best.n_legitimate == legit_n) & (best.n_impostor == impostor_n)].cohort_sessions.iloc[0])
        legit, impostor = users[:legit_n], users[legit_n:legit_n + impostor_n]
        part = cohort_mod.split_claims(sessions[sessions.sessions == k], legit, impostor)
        cell = cells[(cells.n_legitimate == legit_n) & (cells.n_impostor == impostor_n) & (cells.sessions == k)
                     & (cells.method == "cohort")].iloc[0]
        for y, genuine, colour, label in ((1, True, CLAIMED, "genuine"), (0, False, CLOSER, "impostor")):
            values = part[part.genuine == genuine].cohort
            ax.scatter(values, y + rng.uniform(-0.25, 0.25, len(values)), s=10, color=colour, alpha=0.6,
                       label=f"{label} ({len(values)})")
        ax.axvline(cell.threshold, color=QUERY, linewidth=1.5)
        ax.axvline(0.5, color=FARTHER, linewidth=1, linestyle=":")
        ax.set_yticks([0, 1], ["impostor", "genuine"], fontsize=8)
        ax.set_ylim(-0.6, 1.6)
        ax.set_title(f"{legit_n} legit vs {impostor_n} impostors, {k} sessions: EER {cell.eer:.2f}, "
                     f"threshold {cell.threshold:.2f}", fontsize=9)
        ax.grid(alpha=0.3, axis="x")
    for ax in axes.flat[len(splits):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("cohort score of the session (accepted right of the black line)")
    axes[0][0].legend(fontsize=7, loc="upper left")
    fig.suptitle(title, fontsize=10)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ (default: the one config.yaml selects)")
    parser.add_argument("--user", help="claimed user to draw (default: the first legitimate user of the draw)")
    parser.add_argument("--sessions", type=int, help="sessions per user (default: 19's choice for the 1-legitimate split)")
    parser.add_argument("--strokes", type=int, default=6, help="strokes per claim figure, spread over their rank range")
    parser.add_argument("--max-sessions", type=int, default=10, help="as in 19")
    parser.add_argument("--strokes-per-session", type=int, default=40, help="as in 19")
    parser.add_argument("--cap", type=float, default=0.5, help="as in 19")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    folder = group / "cohort"
    if not (folder / "sessions.csv").exists():
        raise SystemExit(f"No {folder / 'sessions.csv'}: run 19_cohort_score.py {group.name} first")
    sessions = pd.read_csv(folder / "sessions.csv")
    cells = pd.read_csv(folder / "cells.csv")
    best = pd.read_csv(folder / "best.csv")
    config = cfg_mod.load_config(next(group.glob("*/config.yaml")))
    users, order = cohort_mod.draw_all(config, config["seed"])
    user = args.user or users[0]
    k = args.sessions or int(best[best.n_legitimate == best.n_legitimate.min()].cohort_sessions.iloc[0])
    if k not in set(sessions.sessions):
        raise SystemExit(f"19 scored sessions {sorted(set(sessions.sessions))}, not {k}")

    cohort_mod.load_nearest()
    _, libraries = cohort_mod.build_libraries(users, order, k, args.strokes_per_session, max(sessions.sessions), config)
    at_k = sessions[sessions.sessions == k]
    genuine = at_k[at_k.genuine & (at_k.claimed == user)].sort_values("cohort")
    impostor = at_k[~at_k.genuine & (at_k.claimed == user)].sort_values("cohort")
    out = folder / "plots"
    out.mkdir(exist_ok=True)
    claims = [(genuine.iloc[len(genuine) // 2], "the median-scoring genuine session", f"claim_{user}_genuine.png"),
              (impostor.iloc[len(impostor) // 2], "the median-scoring impostor session (a typical one)",
               f"claim_{user}_impostor_typical.png"),
              (impostor.iloc[-1], "the highest-scoring impostor session (the most dangerous)",
               f"claim_{user}_impostor_top.png")]
    for claim, why, name in claims:
        plot_claim(claim, users, libraries, config, args.cap, args.strokes, out / name, why)
    plot_scores(sessions, cells, best, users, out / "scores_per_split.png",
                f"runs/{group.name}: cohort score of every claim per split, at 19's chosen sessions "
                f"(dots jittered vertically; dotted = 0.5, no evidence)")
    cohort_mod.save_nearest()
    print(f"Claimed user: {user}  Sessions: {k}  Scores: genuine {claims[0][0].cohort:.3f}, typical impostor "
          f"{claims[1][0].author} {claims[1][0].cohort:.3f}, top impostor {claims[2][0].author} {claims[2][0].cohort:.3f}")
    print(f"Output: {out}/ ({', '.join(name for *_, name in claims)}, scores_per_split.png)")


if __name__ == "__main__":
    main()
