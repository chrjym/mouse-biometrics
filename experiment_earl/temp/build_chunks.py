"""
Build (t, t+1) chunks from vectors.csv.

For every consecutive pair of rows (t, t+1):
  - point t is translated to the origin (0, 0)
  - point t+1 is expressed relative to point t (i.e. point_t+1 - point_t)

So each chunk is just two 2D points:
    p0 = (0, 0)
    p1 = (x[t+1] - x[t], y[t+1] - y[t])

which is exactly the displacement vector between the two frames.
The original absolute coordinates and timestamps are kept alongside
for reference/debugging.

Output: chunks.csv (one row per chunk).
"""

import csv
from pathlib import Path

INPUT_PATH = Path("./vectors.csv")
OUT_CSV = Path("./chunks.csv")


def load_rows(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                {
                    "target_time": float(r["target_time"]),
                    "timestamp": float(r["timestamp"]),
                    "x": float(r["x"]),
                    "y": float(r["y"]),
                }
            )
    return rows


def build_chunks(rows):
    """Build one chunk per consecutive pair (t, t+1)."""
    chunks = []
    for i in range(len(rows) - 1):
        t0, t1 = rows[i], rows[i + 1]

        # t is normalized to the origin
        p0_rel = (0.0, 0.0)
        # t+1 expressed relative to t
        p1_rel = (t1["x"] - t0["x"], t1["y"] - t0["y"])

        chunks.append(
            {
                "chunk_index": i,
                "t": t0["target_time"],
                "t_plus_1": t1["target_time"],
                # original absolute positions, kept for reference
                "t_abs": (t0["x"], t0["y"]),
                "t_plus_1_abs": (t1["x"], t1["y"]),
                # normalized/relative positions -- this is the actual chunk data
                "t_rel": p0_rel,
                "t_plus_1_rel": p1_rel,
            }
        )
    return chunks


def save_csv(chunks, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "chunk_index",
                "t",
                "t_plus_1",
                "t_x_abs",
                "t_y_abs",
                "t_plus_1_x_abs",
                "t_plus_1_y_abs",
                "t_x_rel",
                "t_y_rel",
                "t_plus_1_x_rel",
                "t_plus_1_y_rel",
            ]
        )
        for c in chunks:
            writer.writerow(
                [
                    c["chunk_index"],
                    c["t"],
                    c["t_plus_1"],
                    c["t_abs"][0],
                    c["t_abs"][1],
                    c["t_plus_1_abs"][0],
                    c["t_plus_1_abs"][1],
                    c["t_rel"][0],
                    c["t_rel"][1],
                    c["t_plus_1_rel"][0],
                    c["t_plus_1_rel"][1],
                ]
            )


if __name__ == "__main__":
    rows = load_rows(INPUT_PATH)
    chunks = build_chunks(rows)

    save_csv(chunks, OUT_CSV)

    print(f"Built {len(chunks)} chunks from {len(rows)} rows.")
    print("First chunk:", chunks[0])
    print("Second chunk:", chunks[1])
