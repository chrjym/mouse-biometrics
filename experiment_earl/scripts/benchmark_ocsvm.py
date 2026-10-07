#!/usr/bin/env python3
"""Benchmark a One-Class SVM on per-chunk path features (settings in configs/ocsvm.toml) against the concave hull."""

import argparse
import csv
import json
import pickle
import random
import resource
import time
import tomllib
from pathlib import Path

import numpy as np
from shapely import concave_hull, contains_xy
from shapely.geometry import MultiPoint
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, RobustScaler, StandardScaler
from sklearn.svm import OneClassSVM

from features import FEATURES, session_features

ROOT = Path(__file__).resolve().parents[1]
SCALERS = {"standard": StandardScaler, "robust": RobustScaler, "none": None}


def equal_error_rate(genuine: list[float], impostor: list[float]) -> float:
    """EER over session scores; a higher score means more likely genuine."""
    genuine, impostor = np.sort(genuine), np.sort(impostor)
    if not len(genuine) or not len(impostor):
        return float("nan")
    thresholds = np.unique(np.concatenate([genuine, impostor, [np.inf]]))
    far = 1 - np.searchsorted(impostor, thresholds, side="left") / len(impostor)  # impostors accepted
    frr = np.searchsorted(genuine, thresholds, side="left") / len(genuine)  # genuine rejected
    best = np.argmin(np.abs(far - frr))
    return float((far[best] + frr[best]) / 2)


def window_scores(chunk_scores: np.ndarray, size: int, stride: int) -> np.ndarray:
    """Mean chunk score over every `size` consecutive moving seconds (0 = the whole session)."""
    if size == 0:
        return chunk_scores.mean(keepdims=True)
    if len(chunk_scores) < size:
        return np.empty(0)
    total = np.cumsum(np.insert(chunk_scores, 0, 0.0))
    return ((total[size:] - total[:-size]) / size)[::stride]


def window_eers(sessions: list[tuple[np.ndarray, bool]], windows: list[int], stride: int) -> dict[str, float]:
    """EER per window size, pooling the windows of all genuine vs all impostor test sessions."""
    eers = {}
    for size in windows:
        genuine = [window_scores(s, size, stride) for s, is_impostor in sessions if not is_impostor]
        impostor = [window_scores(s, size, stride) for s, is_impostor in sessions if is_impostor]
        eers[str(size)] = equal_error_rate(np.concatenate(genuine), np.concatenate(impostor))
    return eers


def load_labels(labels_path: Path, test_dir: Path) -> dict[str, list[tuple[Path, bool]]]:
    """Labeled test sessions per user as (path, is_impostor)."""
    with labels_path.open(newline="") as handle:
        labels = {row["filename"]: row["is_illegal"] == "1" for row in csv.DictReader(handle)}
    sessions: dict[str, list[tuple[Path, bool]]] = {}
    for path in sorted(test_dir.glob("*/session_*")):
        if path.name in labels:
            sessions.setdefault(path.parent.name, []).append((path, labels[path.name]))
    return sessions


def build_svm(config: dict):
    """Column selection + log transform + scaler + One-Class SVM, as one sklearn pipeline."""
    feats, svm = config["features"], config["svm"]
    columns = [FEATURES.index(name) for name in feats["use"]]
    logged = [i for i, name in enumerate(feats["use"]) if name in feats["log_transform"]]

    def prepare(X: np.ndarray) -> np.ndarray:
        X = X[:, columns].copy()
        X[:, logged] = np.sign(X[:, logged]) * np.log1p(np.abs(X[:, logged]))
        return X

    steps = [FunctionTransformer(prepare)]
    if SCALERS[feats["scaler"]]:
        steps.append(SCALERS[feats["scaler"]]())
    steps.append(OneClassSVM(kernel=svm["kernel"], nu=svm["nu"], gamma=svm["gamma"],
                             degree=svm["degree"], coef0=svm["coef0"]))
    return make_pipeline(*steps)


def benchmark_user(user_dir: Path, tests: list[tuple[Path, bool]], config: dict) -> dict:
    enroll, feats, scoring = config["enrollment"], config["features"], config["scoring"]
    extract = lambda path: session_features(
        path, enroll["interval"], feats["pause_ms"], feats["turn_degrees"], feats["resample_ms"]
    )
    rng = random.Random(f"{enroll['seed']}-{user_dir.name}")
    sessions = sorted(path for path in user_dir.iterdir() if path.is_file())
    selected = rng.sample(sessions, enroll["sessions"])

    start = time.perf_counter()
    train = np.vstack([extract(path) for path in selected])
    test = [(extract(path), is_impostor) for path, is_impostor in tests]
    test = [(X, is_impostor) for X, is_impostor in test if len(X)]
    feature_s = time.perf_counter() - start
    if 0 < enroll["max_train_chunks"] < len(train):
        train = train[rng.sample(range(len(train)), enroll["max_train_chunks"])]
    all_test = np.vstack([X for X, _ in test])

    svm = build_svm(config)
    start = time.perf_counter()
    svm.fit(train)
    fit_s = time.perf_counter() - start
    start = time.perf_counter()
    svm.decision_function(all_test)
    predict_s = time.perf_counter() - start

    if scoring["chunk_score"] == "distance":
        chunk_score = lambda X: svm.decision_function(X)
    else:
        chunk_score = lambda X: (svm.predict(X) == 1).astype(float)
    svm_scores = [(chunk_score(X), is_impostor) for X, is_impostor in test]
    windows, stride = scoring["windows"], scoring["window_stride"]

    result = {
        "user_id": user_dir.name,
        "sessions": [path.name for path in selected],
        "train_chunks": len(train),
        "test_sessions": len(test),
        "test_chunks": len(all_test),
        "feature_extraction_s": feature_s,
        "svm": {
            "fit_s": fit_s,
            "predict_us_per_chunk": predict_s / len(all_test) * 1e6,
            "model_kb": len(pickle.dumps(svm[-1])) / 1024,
            "support_vectors": len(svm[-1].support_vectors_),
            "eer": window_eers(svm_scores, windows, stride),
        },
    }

    if scoring["compare_hull"]:
        dx, dy = FEATURES.index("dx"), FEATURES.index("dy")
        hull = concave_hull(MultiPoint(train[:, [dx, dy]]), ratio=scoring["concave_ratio"])
        hull_scores = [(contains_xy(hull, X[:, dx], X[:, dy]).astype(float), is_impostor) for X, is_impostor in test]
        result["hull_eer"] = window_eers(hull_scores, windows, stride)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/ocsvm.toml")
    args = parser.parse_args()
    with args.config.open("rb") as handle:
        config = tomllib.load(handle)
    data = config["data"]
    unknown = set(config["features"]["use"]) - set(FEATURES)
    if unknown:
        parser.error(f"unknown features in config: {sorted(unknown)}; choose from {FEATURES}")

    tests = load_labels(ROOT / data["labels"], ROOT / data["test_dir"])
    user_dirs = sorted(path for path in (ROOT / data["train_dir"]).iterdir() if path.is_dir())
    if data["users"]:
        user_dirs = [path for path in user_dirs if path.name in set(data["users"])]

    windows = [str(size) for size in config["scoring"]["windows"]]
    window_label = lambda size: "session" if size == "0" else f"{size}s"
    print(f"Config: {args.config}")
    print(f"Features: {', '.join(config['features']['use'])}  (resample {config['features']['resample_ms']} ms)")
    print(f"{'user':7} {'train':>7} {'test':>8} {'feat s':>7} {'fit s':>6} {'µs/chunk':>8} {'KB':>4} {'SVs':>5} | "
          f"SVM EER by window: " + " ".join(f"{window_label(w):>7}" for w in windows))
    results = []
    for user_dir in user_dirs:
        r = benchmark_user(user_dir, tests.get(user_dir.name, []), config)
        results.append(r)
        s = r["svm"]
        print(f"{r['user_id']:7} {r['train_chunks']:7,} {r['test_chunks']:8,} {r['feature_extraction_s']:7.2f} "
              f"{s['fit_s']:6.2f} {s['predict_us_per_chunk']:8.1f} {s['model_kb']:4.0f} {s['support_vectors']:5} | "
              f"{'':19}" + " ".join(f"{s['eer'][w]:7.1%}" for w in windows))

    mean_eer = {"svm": {w: float(np.nanmean([r["svm"]["eer"][w] for r in results])) for w in windows}}
    if config["scoring"]["compare_hull"]:
        mean_eer["hull"] = {w: float(np.nanmean([r["hull_eer"][w] for r in results])) for w in windows}
    print(f"{'Mean EER':>62}   " + " ".join(f"{window_label(w):>7}" for w in windows))
    for model, eers in mean_eer.items():
        print(f"{model:>62}   " + " ".join(f"{eers[w]:7.1%}" for w in windows))
    peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(f"Peak process memory: {peak_mb:.0f} MB")

    output = ROOT / data["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        json.dump({"config": config, "mean_eer": mean_eer, "peak_memory_mb": peak_mb, "users": results},
                  handle, indent=2)
        handle.write("\n")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
