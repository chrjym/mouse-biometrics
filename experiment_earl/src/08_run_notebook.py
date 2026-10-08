#!/usr/bin/env python3
"""Execute notebooks/session_progression.ipynb for a run and save the executed copy in runs/<run>/notebooks/."""

import argparse
import os
from importlib import import_module

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

cfg_mod = import_module("00_config")

TEMPLATE = cfg_mod.ROOT / "notebooks" / "session_progression.ipynb"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    cfg_mod.add_run_argument(parser)
    parser.add_argument("--timeout", type=int, default=3600, help="seconds allowed for the whole notebook")
    args = parser.parse_args()
    _, run = cfg_mod.open_run(args.run)
    os.environ["EARL_RUN"] = run.name  # the notebook picks the same run folder

    notebook = nbformat.read(TEMPLATE, 4)
    ExecutePreprocessor(timeout=args.timeout, kernel_name="python3").preprocess(
        notebook, {"metadata": {"path": str(TEMPLATE.parent)}})
    out = run / "notebooks" / TEMPLATE.name
    out.parent.mkdir(exist_ok=True)
    nbformat.write(notebook, out)
    print(f"Output: {out}")


if __name__ == "__main__":
    main()
