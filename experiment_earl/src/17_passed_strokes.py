#!/usr/bin/env python3
"""Passed sessions at each split's best setting, their strokes trimmed to the first --window seconds, and plots from (0,0)."""

import argparse
import json
import os
from pathlib import Path

import matplotlib
import pandas as pd
import yaml

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "earl_simulation.ipynb"


def notebook_code() -> dict:
    """The simulation notebook's code up to matched_chunks, so sessions are drawn and scored exactly as in the run."""
    code, cwd = {}, Path.cwd()
    os.chdir(NOTEBOOK.parent)
    try:
        for cell in json.loads(NOTEBOOK.read_text())["cells"]:
            if cell["cell_type"] != "code":
                continue
            source = "".join(cell["source"]).replace("cache=True", "cache=False")  # numba cannot file-cache exec'd code
            exec(source, code)
            if "def matched_chunks" in source:
                return code
    finally:
        os.chdir(cwd)
    raise RuntimeError(f"matched_chunks not found in {NOTEBOOK}")


def score_sessions(group: Path, code: dict) -> pd.DataFrame:
    """One row per tested session of every user at every split's best setting, with its library and pass verdict."""
    rows = []
    for b in pd.read_csv(group / "best" / "best_rows.csv").itertuples():
        config = yaml.safe_load((group / b.run / "config.yaml").read_text())
        k = int(b.sessions)
        _, _, order = code["draw_users"](config, config["seed"])
        start = len(order[b.user]) - k if b.kind == "legitimate" else 0  # legitimate: own last k; impostor: first k
        library = [code["dataset_session"](b.profile, n, config) for n in order[b.profile][:k]]
        passed = 0
        for position, name in enumerate(order[b.user][start:start + k], start):
            session = code["dataset_session"](b.user, name, config)
            hits = code["matched_chunks"](session, library, config)
            ok = hits / max(session.n_chunks, 1) >= config["match_shape_ratio"]
            passed += ok
            rows.append({"split": f"{b.n_legitimate}x{b.n_impostor}", "sensitivity": b.sensitivity, "sessions": k,
                         "kind": b.kind, "user": b.user, "profile": b.profile, "position": position, "session": name,
                         "matched": hits, "strokes": session.n_chunks, "passed": ok})
        if passed != b.passed:
            raise ValueError(f"{b.run} {b.user}: {passed} passed here, {b.passed} in best_rows.csv")
    return pd.DataFrame(rows)


def trim(points: pd.DataFrame, window: float) -> pd.DataFrame:
    """Points within the first `window` seconds of their stroke."""
    return points[points.t_s - points.groupby("stroke").t_s.transform("first") <= window]


def plot(strokes: list[tuple[pd.DataFrame, str, str | None]], title: str, path: Path, first_only: bool) -> None:
    """Strokes shifted to start at (0,0); blue = move, orange = drag; end dots and labels for first-stroke plots."""
    fig, ax = plt.subplots(figsize=(8, 8))
    for g, kind, label in strokes:
        dx, dy = g.x - g.x.iloc[0], g.y - g.y.iloc[0]
        color = "tab:orange" if kind == "drag" else "tab:blue"
        if first_only:
            ax.plot(dx, dy, "-o", ms=2.5, lw=1.2, color=color, alpha=.8)
            ax.plot(dx.iloc[-1], dy.iloc[-1], "o", color="red", ms=4)
            ax.annotate(label, (dx.iloc[-1], dy.iloc[-1]), fontsize=7, xytext=(3, 3), textcoords="offset points")
        else:
            ax.plot(dx, dy, color=color, lw=.5, alpha=.25)
    ax.plot(0, 0, "o", color="green", ms=6)
    ax.axhline(0, c="grey", lw=.5)
    ax.axvline(0, c="grey", lw=.5)
    ax.set_aspect("equal")
    ax.invert_yaxis()  # screen coordinates grow downward
    ax.set(title=title, xlabel="Δx (px)", ylabel="Δy (px)")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def export_user(group: Path, out: Path, rows: pd.DataFrame, window: float) -> dict:
    """Trimmed points, first-stroke table and both plots for one user's passed sessions in one split."""
    r0 = rows.iloc[0]
    (out / "trimmed").mkdir(parents=True, exist_ok=True)
    every, firsts, table = [], [], []
    for r in rows.itertuples():
        points = pd.read_csv(group / "strokes" / r.user / f"{r.session}_points.csv")
        kinds = pd.read_csv(group / "strokes" / r.user / f"{r.session}.csv").set_index("stroke").kind
        short = trim(points, window)
        short.to_csv(out / "trimmed" / f"{r.session}_points_{window:g}s.csv", index=False)
        groups = list(short.groupby("stroke"))
        every += [(g, kinds[s], None) for s, g in groups]
        s, g = groups[0]
        firsts.append((g, kinds[s], str(r.position)))
        table.append({"position": r.position, "session": r.session, "stroke": s, "kind": kinds[s], "points": len(g),
                      "end_dx": g.x.iloc[-1] - g.x.iloc[0], "end_dy": g.y.iloc[-1] - g.y.iloc[0],
                      "session_strokes": len(groups), "points_before": len(points), "points_after": len(short)})
    pd.DataFrame(table).to_csv(out / "first_strokes.csv", index=False)
    setting = f"{r0.split}, {r0.sensitivity}, {r0.sessions}"
    plot(every, f"{r0.user}: {len(rows)} passed sessions ({setting}), {len(every):,} strokes, first {window:g} s, from (0,0)",
         out / f"all_strokes_{window:g}s.png", first_only=False)
    plot(firsts, f"{r0.user}: first stroke of each of the {len(rows)} passed sessions ({setting}), first {window:g} s",
         out / f"first_stroke_{window:g}s.png", first_only=True)
    return {"split": r0.split, "kind": r0.kind, "user": r0.user, "passed_sessions": len(rows), "strokes": len(every)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash", required=True, help="run group under runs/, e.g. 19399f (needs best/ and strokes/)")
    parser.add_argument("--window", type=float, default=0.5, help="seconds kept from the start of each stroke")
    args = parser.parse_args()

    group = ROOT / "runs" / args.hash
    out = group / f"passed_strokes_{args.window:g}s"
    scored = score_sessions(group, notebook_code())
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "session_results.csv", index=False)
    passed = scored[scored.passed]
    summary = [export_user(group, out / split / user, rows, args.window)
               for (split, user), rows in passed.groupby(["split", "user"], sort=False)]
    pd.DataFrame(summary).to_csv(out / "summary.csv", index=False)
    print(f"{len(scored)} sessions scored, {len(passed)} passed, {len(summary)} user folders")
    print(f"Output: {out}/")


if __name__ == "__main__":
    main()
