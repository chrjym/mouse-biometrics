"""Shared config and Balabit session loader for the EARL shape-matching experiment."""

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
INVALID_COORDINATE = 65535  # Balabit logging glitch, not a position


def load_config(path: Path | None = None, **overrides) -> dict:
    with (path or ROOT / "config.yaml").open() as handle:
        config = yaml.safe_load(handle)
    config.update(overrides)
    return config


def list_users(config: dict) -> list[str]:
    return sorted(p.name for p in (ROOT / config["dataset_dir"]).iterdir() if p.is_dir())


def list_sessions(config: dict, user: str) -> list[Path]:
    return sorted(p for p in (ROOT / config["dataset_dir"] / user).iterdir() if p.is_file())


def load_session(path: Path) -> pd.DataFrame:
    """Columns t (seconds from the first event), x, y, button, state, in time order.

    Scroll rows carry no path and glitch rows (x or y = 65535) are not positions, so both are dropped.
    The sort is stable because many Balabit timestamps tie.
    """
    df = pd.read_csv(path, usecols=["client timestamp", "button", "state", "x", "y"])
    df = df.rename(columns={"client timestamp": "t"})
    df = df.dropna(subset=["t", "x", "y"])
    df = df[(df["button"] != "Scroll") & (df["x"] < INVALID_COORDINATE) & (df["y"] < INVALID_COORDINATE)]
    df = df.sort_values("t", kind="stable").reset_index(drop=True)
    df["t"] = df["t"] - df["t"].iloc[0] if len(df) else df["t"]
    return df[["t", "x", "y", "button", "state"]]
