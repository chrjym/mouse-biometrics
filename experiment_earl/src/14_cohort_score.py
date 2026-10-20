#!/usr/bin/env python3
"""Cohort scoring for one hash folder: a session counts for its claimed user only if its strokes lie closer to that user's library than to other people's; EER and best user accuracy per split, next to 13's, in runs/<hash>/cohort/."""

import argparse
import pickle
import time
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
plot_mod = import_module("09_plot_matches")

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = cfg_mod.CACHE_DIR / "nearest.pkl"
METHODS = ("raw", "cohort")
_NEAREST: dict = {}  # (query session, library name, settings) -> nearest DTW cost per query stroke


def load_nearest() -> None:
    if CACHE_PATH.exists():
        _NEAREST.update(pickle.loads(CACHE_PATH.read_bytes()))


def save_nearest() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("wb") as handle:  # stream, so the cache is never held twice in memory
        pickle.dump(_NEAREST, handle)


@njit(cache=True)
def _dtw_cost(a, b, band, limit, prev, cur):
    """Banded DTW cost between paths a and b, or inf once every cell of a row exceeds `limit`."""
    n = a.shape[0]
    prev[:] = np.inf
    prev[0] = 0.0
    for i in range(n):
        cur[:] = np.inf
        row_min = np.inf
        for j in range(max(0, i - band), min(n - 1, i + band) + 1):
            dx, dy = a[i, 0] - b[j, 0], a[i, 1] - b[j, 1]
            value = np.sqrt(dx * dx + dy * dy) + min(prev[j], prev[j + 1], cur[j])
            cur[j + 1] = value
            row_min = min(row_min, value)
        if row_min > limit:
            return np.inf
        prev, cur = cur, prev
    return prev[n]


@njit(parallel=True, cache=True)
def nearest(queries, library, band, cap):
    """Per query path: the lowest DTW cost to any library path, capped at `cap` (the best so far prunes the rest)."""
    n = queries.shape[1]
    best = np.full(queries.shape[0], cap)
    for q in prange(queries.shape[0]):
        prev, cur = np.empty(n + 1), np.empty(n + 1)
        for k in range(library.shape[0]):
            cost = _dtw_cost(queries[q], library[k], band, best[q], prev, cur)
            if cost < best[q]:
                best[q] = cost
    return best


def build_library(sessions: list, size: int) -> dict[int, np.ndarray]:
    """The strokes of `sessions`, cut to `size` evenly spaced strokes (all kinds pooled), split back by kind. Equal
    sizes matter: a library with more strokes is closer to everything (user16's and user23's ~1,000-stroke
    2-session profiles let almost every impostor through)."""
    kinds = np.concatenate([np.full(len(s.paths[k]), k) for s in sessions for k in sorted(s.paths)])
    paths = np.concatenate([s.paths[k] for s in sessions for k in sorted(s.paths)])
    keep = np.unique(np.linspace(0, len(paths) - 1, size).round().astype(int)) if len(paths) > size else slice(None)
    kinds, paths = kinds[keep], paths[keep]
    return {int(k): paths[kinds == k] for k in np.unique(kinds)}


def library_nearest(query, name: tuple, library: dict, config: dict, cap: float) -> np.ndarray:
    """Nearest DTW cost per point for every query stroke (kinds in a fixed order) against a library (cached by name)."""
    n = config["resample_n"]
    key = (query.key, name, match_mod.segmentation(config), config["dtw_band"], cap)
    if key not in _NEAREST:
        band = int(round(config["dtw_band"] * n))
        parts = [nearest(paths, library[kind], band, cap * n) / n if len(paths) and kind in library
                 else np.full(len(paths), cap) for kind, paths in sorted(query.paths.items())]
        _NEAREST[key] = np.concatenate(parts) if parts else np.zeros(0)
    return _NEAREST[key]


def claim_scores(query, claimed: str, others: list[str], libraries: dict, config: dict,
                 cap: float) -> tuple[float, float]:
    """Raw score = minus the mean nearest cost to the claimed user's profile. Cohort score = mean over strokes of
    the share of other people whose background library is farther than the claimed profile (ties count half;
    0.5 = no evidence)."""
    own = library_nearest(query, *libraries[("profile", claimed)], config, cap)
    if not len(own):
        return -cap, 0.5
    rest = np.array([library_nearest(query, *libraries[("background", w)], config, cap) for w in others])
    rank = ((rest > own).sum(axis=0) + 0.5 * (rest == own).sum(axis=0)) / len(others)
    return -float(own.mean()), float(rank.mean())


def fill(user: str, entries: list, budget: int, config: dict) -> list:
    """Sessions from `entries`, in order, until they hold at least `budget` strokes (all of them if they never do)."""
    sessions, strokes = [], 0
    for folder, name in entries:
        if strokes >= budget:
            break
        session = match_mod.dataset_session(user, name, config, folder)
        sessions.append(session)
        strokes += sum(len(p) for p in session.paths.values())
    return sessions


def build_libraries(users: list[str], order: dict, k: int, per_session: int, reserve: int,
                    config: dict) -> tuple[dict, dict]:
    """Per (role, user): the sessions used, and (cache name, library of k x `per_session` strokes). Profiles come
    from the front half of the pool minus the last `reserve` sessions, backgrounds from the back half."""
    budget = k * per_session
    sources = {}
    for u in users:
        half = (len(order[u]) - reserve) // 2
        sources[("profile", u)] = fill(u, order[u][:half], budget, config)
        sources[("background", u)] = fill(u, order[u][half:2 * half], budget, config)
    sizes = {key: sum(len(p) for s in sessions for p in s.paths.values()) for key, sessions in sources.items()}
    short = {f"{role} {u}": n for (role, u), n in sizes.items() if n < budget}
    if short:
        print(f"  {k} sessions: libraries below {budget} strokes, used whole: {short}")
    libraries = {key: ((*key, budget, tuple(s.key for s in sessions)), build_library(sessions, budget))
                 for key, sessions in sources.items()}
    return sources, libraries


def score_sessions(users: list[str], order: dict, k_values: list[int], per_session: int, config: dict,
                   cap: float, reserve: int | None = None) -> pd.DataFrame:
    """Every claim needed by any split: each user's last k sessions as themselves, and each user's first k sessions
    as every other user. Every library holds k x `per_session` strokes: a profile from the front half of the user's
    pool (minus the last `reserve` (default: max k) test sessions), another person's background from the back half."""
    reserve = reserve or max(k_values)
    rows = []
    for k in k_values:
        budget = k * per_session
        sources, libraries = build_libraries(users, order, k, per_session, reserve, config)
        for author in users:
            claims = [(author, entry, True) for entry in order[author][-k:]]
            claims += [(claimed, entry, False) for claimed in users if claimed != author for entry in order[author][:k]]
            for claimed, (folder, name), genuine in claims:
                query = match_mod.dataset_session(author, name, config, folder)
                others = [w for w in users if w not in (claimed, author)]
                raw, cohort = claim_scores(query, claimed, others, libraries, config, cap)
                rows.append({"sessions": k, "library_strokes": budget,
                             "profile_sessions": len(sources[("profile", claimed)]), "author": author,
                             "claimed": claimed, "session": name, "genuine": genuine, "raw": raw, "cohort": cohort})
        used = [len(v) for (role, _), v in sources.items() if role == "profile"]
        print(f"{k} sessions scored (libraries of {budget} strokes, profiles use {min(used)}–{max(used)} sessions)",
              flush=True)
    return pd.DataFrame(rows)


def eer(genuine: np.ndarray, impostor: np.ndarray) -> float:
    """Equal error rate: where the share of genuine sessions rejected meets the share of impostor sessions accepted."""
    thresholds = np.unique(np.concatenate([genuine, impostor, [np.inf]]))
    frr = np.array([(genuine < t).mean() for t in thresholds])
    far = np.array([(impostor >= t).mean() for t in thresholds])
    i = int(np.argmin(np.abs(frr - far)))
    return float((frr[i] + far[i]) / 2)


def at_threshold(part: pd.DataFrame, legit: list[str], method: str, ratio: float, t: float) -> dict:
    """Users through at acceptance threshold `t` (13's rule: a user is through at `ratio` of their sessions accepted;
    an impostor at `ratio` against any one legitimate user), user accuracy and session accuracy."""
    genuine, impostor = part[part.genuine], part[~part.genuine]
    legit_share = genuine.assign(ok=genuine[method] >= t).groupby("author")["ok"].mean()
    impostor_share = impostor.assign(ok=impostor[method] >= t).groupby(["author", "claimed"])["ok"].mean()
    legit_through = int((legit_share >= ratio).sum())
    impostor_through = int((impostor_share.groupby(level=0).max() >= ratio).sum())
    n_impostor = impostor["author"].nunique()
    return {"threshold": t, "legit_through": legit_through, "legit_users": len(legit),
            "impostor_through": impostor_through, "impostor_users": n_impostor,
            "user_accuracy": (legit_through / len(legit) + 1 - impostor_through / n_impostor) / 2,
            "session_accuracy": ((genuine[method] >= t).mean() + 1 - (impostor[method] >= t).mean()) / 2}


def best_threshold(part: pd.DataFrame, legit: list[str], method: str, ratio: float) -> dict:
    """The acceptance threshold with the highest user accuracy; ties go to session accuracy."""
    candidates = [at_threshold(part, legit, method, ratio, t)
                  for t in np.unique(np.concatenate([part[method].to_numpy(), [np.inf]]))]
    return max(candidates, key=lambda c: (c["user_accuracy"], c["session_accuracy"]))


def split_claims(at_k: pd.DataFrame, legit: list[str], impostor: list[str]) -> pd.DataFrame:
    """The claims one split tests: legitimate users as themselves, impostors as each legitimate user."""
    return at_k[(at_k.genuine & at_k.author.isin(legit)) |
                (~at_k.genuine & at_k.author.isin(impostor) & at_k.claimed.isin(legit))]


def draw_all(config: dict, seed: int) -> tuple[list[str], dict]:
    """All 10 users in draw order (every split's legitimate users are a prefix of it) and their session orders."""
    legit, impostor, order = plot_mod.draw_users({**config, "n_legitimate": 9, "n_impostor": 1}, seed)
    return legit + impostor, order


def score_cells(sessions: pd.DataFrame, users: list[str], splits: list[tuple[int, int]], ratio: float) -> pd.DataFrame:
    """Per (split, sessions, method): EER over all claims of the split and the best threshold's user accuracy."""
    rows = []
    for n_legit, n_impostor in splits:
        legit, impostor = users[:n_legit], users[n_legit:n_legit + n_impostor]
        for k, at_k in sessions.groupby("sessions"):
            part = split_claims(at_k, legit, impostor)
            for method in METHODS:
                rows.append({"n_legitimate": n_legit, "n_impostor": n_impostor, "sessions": k, "method": method,
                             "eer": eer(part[part.genuine][method].to_numpy(), part[~part.genuine][method].to_numpy()),
                             **best_threshold(part, legit, method, ratio)})
    return pd.DataFrame(rows)


def pick_best(cells: pd.DataFrame, baseline: pd.DataFrame | None) -> pd.DataFrame:
    """Per split and method, the session count with the highest user accuracy (ties: session accuracy, then fewer
    sessions), next to 13's best (sensitivity matching) for the same split."""
    ranked = cells.sort_values(["n_legitimate", "n_impostor", "method", "user_accuracy", "session_accuracy", "sessions"],
                               ascending=[True, True, True, False, False, True])
    best = ranked.groupby(["n_legitimate", "n_impostor", "method"], as_index=False).head(1)
    wide = best.pivot_table(index=["n_legitimate", "n_impostor"], columns="method",
                            values=["sessions", "user_accuracy", "session_accuracy", "eer", "impostor_through"])
    wide.columns = [f"{method}_{value}" for value, method in wide.columns]
    wide = wide.reset_index()
    if baseline is not None:
        keep = baseline[["n_legitimate", "n_impostor", "sensitivity", "sessions", "user_accuracy", "session_accuracy",
                         "impostor_through"]]
        keep = keep.rename(columns={c: f"match_{c}" for c in keep.columns if c not in ("n_legitimate", "n_impostor")})
        wide = keep.merge(wide, on=["n_legitimate", "n_impostor"], how="right")
    return wide


def plot(cells: pd.DataFrame, best: pd.DataFrame, path: Path, title: str) -> None:
    """Left: EER per sessions per user, one line per split (solid = cohort, dashed = raw). Right: best user accuracy
    per split for 13's sensitivity matching and the two scores here."""
    fig, (left, right) = plt.subplots(1, 2, figsize=(14, 5), layout="constrained")
    splits = list(best[["n_legitimate", "n_impostor"]].itertuples(index=False, name=None))
    colours = plt.cm.viridis(np.linspace(0, 0.9, len(splits)))
    for colour, (legit, impostor) in zip(colours, splits):
        part = cells[(cells.n_legitimate == legit) & (cells.n_impostor == impostor)]
        for method, style in (("cohort", "-"), ("raw", "--")):
            line = part[part.method == method].sort_values("sessions")
            left.plot(line.sessions, line.eer, style, color=colour, linewidth=2 if method == "cohort" else 1,
                      marker="o" if method == "cohort" else None, markersize=4,
                      label=f"{legit}–{impostor}" if method == "cohort" else None)
    left.axhline(0.5, color="grey", linewidth=1, linestyle=":")
    left.set(xlabel="sessions per user", ylabel="EER (lower = better, 0.5 = chance)", ylim=(0, 0.8),
             title="Equal error rate per split (solid = cohort, dashed = raw distance)")
    left.legend(title="legit–impostors", fontsize=7, ncol=3)
    left.grid(alpha=0.3)

    x = np.arange(len(splits))
    bars = [("match", "13: sensitivity matching", "#bbbbbb"), ("raw", "raw distance", "#7aa6c2"),
            ("cohort", "cohort", "#1f5f8b")]
    bars = [b for b in bars if f"{b[0]}_user_accuracy" in best]
    width = 0.8 / len(bars)
    for i, (prefix, label, colour) in enumerate(bars):
        values = best[f"{prefix}_user_accuracy"].to_numpy()
        right.bar(x + (i - (len(bars) - 1) / 2) * width, values, width * 0.92, color=colour, label=label)
    right.axhline(0.5, color="grey", linewidth=1, linestyle=":")
    right.set_xticks(x, [f"{a}–{b}" for a, b in splits])
    right.set(xlabel="split (legitimate–impostors)", ylabel="best user accuracy (0.5 = chance)", ylim=(0, 1),
              title="Best user accuracy per split (tuned on the same runs: optimistic)")
    right.legend(fontsize=8, loc="upper right")
    right.grid(alpha=0.3, axis="y")
    fig.suptitle(title, fontsize=10)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hash", nargs="?", help="folder under runs/ (default: the one config.yaml selects)")
    parser.add_argument("--max-sessions", type=int, default=10,
                        help="highest sessions per user to score (cost grows with its square; the batch went to 30)")
    parser.add_argument("--strokes-per-session", type=int, default=40,
                        help="every library holds sessions x this many strokes (40 ~ the median strokes per session)")
    parser.add_argument("--cap", type=float, default=0.5,
                        help="DTW cost per point above which strokes count as equally far (the batch shows nothing above 0.1)")
    args = parser.parse_args()
    group = cfg_mod.RUNS / (args.hash or cfg_mod.run_folder_name(cfg_mod.load_config()).split("/")[0])
    folders = sorted(p.parent for p in group.glob("*/config.yaml"))
    if not folders:
        raise SystemExit(f"No runs under {group}")
    config = cfg_mod.load_config(folders[0] / "config.yaml")
    runs = [cfg_mod.load_config(f / "config.yaml") for f in folders]
    splits = sorted({(c["n_legitimate"], c["n_impostor"]) for c in runs})
    k_values = sorted({c["sessions_per_user"] for c in runs if c["sessions_per_user"] <= args.max_sessions})
    if not k_values:
        raise SystemExit(f"No runs with at most {args.max_sessions} sessions per user")

    users, order = draw_all(config, config["seed"])
    short = [u for u in users if len(order[u]) < 3 * max(k_values)]
    if short:
        raise SystemExit(f"Pools too small for {max(k_values)} sessions: {short}")

    load_nearest()
    began = time.monotonic()
    sessions = score_sessions(users, order, k_values, args.strokes_per_session, config, args.cap)
    save_nearest()

    cells = score_cells(sessions, users, splits, config["match_session_ratio"])
    baseline_path = group / "best" / "best.csv"
    baseline = pd.read_csv(baseline_path) if baseline_path.exists() else None
    best = pick_best(cells, baseline)
    out = group / "cohort"
    out.mkdir(exist_ok=True)
    sessions.to_csv(out / "sessions.csv", index=False)
    cells.to_csv(out / "cells.csv", index=False)
    best.to_csv(out / "best.csv", index=False)
    plot(cells, best, out / "cohort.png",
         f"runs/{group.name}, seed {config['seed']}: cohort score = share of other people a stroke is farther from than "
         f"from the claimed user; raw = mean nearest DTW cost; {k_values[0]}–{k_values[-1]} sessions per user")

    show = [c for c in best.columns if c.endswith(("user_accuracy", "eer", "sessions", "sensitivity"))]
    print(best[["n_legitimate", "n_impostor"] + show].round(3).to_string(index=False))
    print(f"Claims: {len(sessions)}  Cached: {len(_NEAREST)}  Time: {time.monotonic() - began:.0f} s")
    print(f"Output: {out}/ (sessions.csv, cells.csv, best.csv, cohort.png)")


if __name__ == "__main__":
    main()
