import pandas as pd
import numpy as np


def extract_vectors(input_file, output_file, interval=1.0):

    # Column names
    columns = [
        "timestamp",
        "client_timestamp",
        "button",
        "state",
        "x",
        "y"
    ]

    # Load the input file
    df = pd.read_csv(
        input_file,
        header=None,
        names=columns
    )

    # Convert required columns to numeric
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")

    # Remove invalid rows
    df = df.dropna(subset=["timestamp", "x", "y"])

    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    # ---------------------------------------------------------
    # Find the first actual record >= each target time
    # ---------------------------------------------------------

    start_time = df["timestamp"].iloc[0]
    end_time = df["timestamp"].iloc[-1]

    target_time = start_time
    selected = []

    while target_time <= end_time:

        # First row whose timestamp >= target_time
        matches = df[df["timestamp"] >= target_time]

        if len(matches) == 0:
            break

        row = matches.iloc[0]

        selected.append({
            "target_time": target_time,
            "timestamp": row["timestamp"],
            "x": row["x"],
            "y": row["y"]
        })

        target_time += interval

    # Create DataFrame
    result = pd.DataFrame(selected)

    # ---------------------------------------------------------
    # Calculate movement vectors
    # ---------------------------------------------------------

    result["vector_x"] = result["x"].diff().fillna(0)
    result["vector_y"] = result["y"].diff().fillna(0)

    # Vector magnitude
    result["vector_magnitude"] = np.sqrt(
        result["vector_x"] ** 2 +
        result["vector_y"] ** 2
    )

    # ---------------------------------------------------------
    # Save output
    # ---------------------------------------------------------

    result.to_csv(output_file, index=False)

    print("Done!")
    print(f"Input : {input_file}")
    print(f"Output: {output_file}")
    print(f"Interval: {interval} seconds")


# =============================================================
# CONFIGURATION
# =============================================================

INPUT_FILE = "./user15/session_0003960194"
OUTPUT_FILE = "vectors.csv"

# Sampling interval in seconds
INTERVAL = 1.0


# =============================================================
# RUN
# =============================================================

extract_vectors(
    INPUT_FILE,
    OUTPUT_FILE,
    INTERVAL
)
