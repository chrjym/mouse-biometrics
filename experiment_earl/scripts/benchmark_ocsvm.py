#!/usr/bin/env python3
"""Compare the concave hull and a One-Class SVM as profiles: cost (time, size, memory) and session-level EER."""

import argparse
import csv
import json
import pickle
import random
import resource
import time
from pathlib import Path

import numpy as np
from shapely import concave_hull, contains_xy
from shapely.geometry import MultiPoint
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

from chunking import build_chunks, build_vectors

ROOT = Path(__file__).resolve().parents[1]


def moving_endpoints(session_path: Path) -> np.ndarray:
    """Chunk end points (dx, dy) of the moving 1-second chunks of one session."""
    chunks = build_chunks(build_vectors(session_path))
    points = [(c["t_plus_1_x_rel"], c["t_plus_1_y_rel"]) for c in chunks]
    points = np.array([p for p in points if p != (0.0, 0.0)]).reshape(-1, 2)
    return points


def equal_error_rate(genuine: list[float], impostor: list[float]) -> float:
    """EER over session scores (fraction of chunks accepted); higher score = more genuine."""
    genuine, impostor = np.array(genuine), np.array(impostor)
    best = (2.0, 1.0)
    for threshold in np.unique(np.concatenate([genuine, impostor, [1.1]])):
        far = np.mean(impostor >= threshold)
        frr = np.mean(genuine < threshold)
        if abs(far - frr) < best[0]:
            best = (abs(far - frr), (far + frr) / 2)
    return best[1]


def load_labels(labels_path: Path, test_dir: Path) -> dict[str, list[tuple[Path, bool]]]:
    """Labeled test sessions per user as (path, is_impostor)."""
    labels = {row["filename"]: row["is_illegal"] == "1" for row in csv.DictReader(labels_path.open())}
    sessions: dict[str, list[tuple[Path, bool]]] = {}
    for path in sorted(test_dir.glob("*/session_*")):
        if path.name in labels:
            sessions.setdefault(path.parent.name, []).append((path, labels[path.name]))
    return sessions


def benchmark_user(user_dir: Path, tests: list[tuple[Path, bool]], args: argparse.Namespace) -> dict:
    sessions = sorted(path for path in user_dir.iterdir() if path.is_file())
    selected = random.Random(f"{args.seed}-{user_dir.name}").sample(sessions, args.sessions)

    start = time.perf_counter()
    train = np.vstack([moving_endpoints(path) for path in selected])
    chunk_s = time.perf_counter() - start

    start = time.perf_counter()
    hull = concave_hull(MultiPoint(train), ratio=args.concave_ratio)
    hull_fit_s = time.perf_counter() - start

    svm = make_pipeline(StandardScaler(), OneClassSVM(nu=args.nu, gamma="scale"))
    start = time.perf_counter()
    svm.fit(train)
    svm_fit_s = time.perf_counter() - start

    test_points = [(moving_endpoints(path), is_impostor) for path, is_impostor in tests]
    test_points = [(points, is_impostor) for points, is_impostor in test_points if len(points)]
    all_test = np.vstack([points for points, _ in test_points])

    start = time.perf_counter()
    contains_xy(hull, all_test[:, 0], all_test[:, 1])
    hull_predict_s = time.perf_counter() - start
    start = time.perf_counter()
    svm.predict(all_test)
    svm_predict_s = time.perf_counter() - start

    scores = {"hull": ([], []), "svm": ([], [])}
    for points, is_impostor in test_points:
        scores["hull"][is_impostor].append(contains_xy(hull, points[:, 0], points[:, 1]).mean())
        scores["svm"][is_impostor].append((svm.predict(points) == 1).mean())

    return {
        "user_id": user_dir.name,
        "train_chunks": len(train),
        "test_sessions": len(test_points),
        "test_chunks": len(all_test),
        "chunking_s": chunk_s,
        "hull": {
            "fit_s": hull_fit_s,
            "predict_us_per_chunk": hull_predict_s / len(all_test) * 1e6,
            "model_kb": len(pickle.dumps(hull)) / 1024,
            "vertices": len(hull.exterior.coords),
            "eer": equal_error_rate(*scores["hull"]),
        },
        "svm": {
            "fit_s": svm_fit_s,
            "predict_us_per_chunk": svm_predict_s / len(all_test) * 1e6,
            "model_kb": len(pickle.dumps(svm)) / 1024,
            "support_vectors": len(svm[-1].support_vectors_),
            "eer": equal_error_rate(*scores["svm"]),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-dir", type=Path, default=ROOT / "datasets/balabit/training_files")
    parser.add_argument("--test-dir", type=Path, default=ROOT / "datasets/balabit/test_files")
    parser.add_argument("--labels", type=Path, default=ROOT / "datasets/balabit/public_labels.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/benchmark_ocsvm.json")
    parser.add_argument("--user", action="append", help="limit to these users (repeatable)")
    parser.add_argument("--sessions", type=int, default=3, help="random training sessions per user")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--nu", type=float, default=0.05, help="One-Class SVM: share of training chunks allowed outside")
    parser.add_argument("--concave-ratio", type=float, default=0.1)
    args = parser.parse_args()

    tests = load_labels(args.labels, args.test_dir)
    user_dirs = sorted(path for path in args.train_dir.iterdir() if path.is_dir())
    if args.user:
        user_dirs = [path for path in user_dirs if path.name in set(args.user)]

    results = []
    print(f"{'user':7} {'train':>7} {'test':>8} | {'fit s':>6} {'µs/chunk':>8} {'KB':>5} {'EER':>5} (hull) | "
          f"{'fit s':>6} {'µs/chunk':>8} {'KB':>5} {'SVs':>5} {'EER':>5} (svm)")
    for user_dir in user_dirs:
        r = benchmark_user(user_dir, tests.get(user_dir.name, []), args)
        results.append(r)
        h, s = r["hull"], r["svm"]
        print(f"{r['user_id']:7} {r['train_chunks']:7,} {r['test_chunks']:8,} | "
              f"{h['fit_s']:6.3f} {h['predict_us_per_chunk']:8.2f} {h['model_kb']:5.0f} {h['eer']:5.1%}        | "
              f"{s['fit_s']:6.3f} {s['predict_us_per_chunk']:8.2f} {s['model_kb']:5.0f} {s['support_vectors']:5} {s['eer']:5.1%}")

    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    for model in ("hull", "svm"):
        print(f"mean EER {model}: {np.mean([r[model]['eer'] for r in results]):.1%}")
    print(f"Peak process memory: {peak_mb:.0f} MB")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as handle:
        json.dump({"settings": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
                   "peak_memory_mb": peak_mb, "users": results}, handle, indent=2)
        handle.write("\n")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
