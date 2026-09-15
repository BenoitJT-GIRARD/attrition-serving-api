"""Rebuild the three extracts from the public IBM dataset, or check the ones already there.

The extracts are not redistributed here. They are a split of IBM's *HR Analytics Employee
Attrition & Performance* sample dataset, and `src/attrition_serving/data/source.py` carries
the correspondence column by column and value by value.

    # download WA_Fn-UseC_-HR-Employee-Attrition.csv from Kaggle, then:
    uv run python scripts/build_extracts.py --source ~/Downloads/WA_Fn-UseC_-HR-Employee-Attrition.csv
    uv run python scripts/build_extracts.py --check      # what is under data/raw/ is that dataset

`--check` is the one to run before quoting a number: it replays the ranges and the value
counts that identify the dataset, and says which column disagrees.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from attrition_serving.config import PATHS
from attrition_serving.data.source import (
    DROPPED_UPSTREAM,
    EXPECTED_DEPARTURES,
    EXPECTED_ROWS,
    EXTRACT_FILES,
    UPSTREAM_FILE,
    columns_of,
    profile,
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build(upstream: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Cut the upstream frame into the three extracts, applying the declared translations."""
    missing = [
        column.upstream
        for column in columns_of("sirh") + columns_of("eval") + columns_of("sondage")
        if column.upstream not in upstream.columns
    ]
    if missing:
        raise SystemExit(f"[fail] the source file has no column {sorted(set(missing))}")

    out: dict[str, pd.DataFrame] = {}
    for extract in EXTRACT_FILES:
        frame = pd.DataFrame(index=upstream.index)
        for column in columns_of(extract):
            values = upstream[column.upstream]
            if column.values:
                unknown = sorted(set(values.astype(str)) - set(column.values))
                if unknown:
                    raise SystemExit(
                        f"[fail] {column.upstream} carries {unknown}, which the mapping in "
                        "data/source.py does not name"
                    )
                values = values.astype(str).map(column.values)
            elif column.name == "eval_number":
                values = "E_" + values.astype(str)
            elif column.name == "code_sondage":
                values = values.astype(str).str.zfill(6)
            elif column.name == "augementation_salaire_precedente":
                values = values.astype(str) + " %"
            frame[column.name] = values
        out[extract] = frame
    return out


def check(directory) -> list[str]:
    """Everything the extracts under `directory` disagree with. Empty means they match."""
    problems: list[str] = []
    for extract, filename in EXTRACT_FILES.items():
        path = directory / filename
        if not path.exists():
            problems.append(f"{filename} is not there")
            continue
        frame = pd.read_csv(path, encoding="utf-8")
        if len(frame) != EXPECTED_ROWS:
            problems.append(f"{filename}: {len(frame)} rows, expected {EXPECTED_ROWS}")
        expected_names = [column.name for column in columns_of(extract)]
        if list(frame.columns) != expected_names:
            problems.append(f"{filename}: columns differ from the ones data/source.py names")
            continue
        for name in expected_names:
            problems += profile(frame, name)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        help=f"the upstream {UPSTREAM_FILE}, downloaded from Kaggle",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the extracts already under data/raw/ instead of writing them",
    )
    args = parser.parse_args()

    if args.check or not args.source:
        problems = check(PATHS.data_raw)
        if problems:
            print(f"[fail] {len(problems)} disagreement(s) with the published dataset:")
            for line in problems[:12]:
                print(f"  {line}")
            return 1
        print(
            f"[ok] {PATHS.data_raw} holds the IBM HR Analytics dataset: {EXPECTED_ROWS} rows, "
            f"{EXPECTED_DEPARTURES} departures, every column within its published profile"
        )
        return 0

    upstream = pd.read_csv(args.source, encoding="utf-8")
    dropped = [name for name in DROPPED_UPSTREAM if name in upstream.columns]
    extracts = build(upstream)
    PATHS.data_raw.mkdir(parents=True, exist_ok=True)
    for extract, frame in extracts.items():
        target = PATHS.data_raw / EXTRACT_FILES[extract]
        frame.to_csv(target, index=False, encoding="utf-8", lineterminator="\n")
        print(f"[ok] {target.name} — {len(frame)} rows, {len(frame.columns)} columns")
    print(f"[info] {len(dropped)} upstream column(s) left out: {', '.join(dropped)}")

    problems = check(PATHS.data_raw)
    if problems:
        print(f"[fail] what was written does not match the published profile ({len(problems)}):")
        for line in problems[:12]:
            print(f"  {line}")
        return 1
    print("[ok] the rebuilt extracts match the profile the repository publishes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
