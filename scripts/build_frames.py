"""Build the joined frame and the feature frame from the three extracts.

    uv run python scripts/build_frames.py

Reads `extrait_sirh.csv`, `extrait_eval.csv` and `extrait_sondage.csv` under `data/raw/`, and
writes `employees_joined.parquet` and `employees_features.parquet` under `data/processed/`.
`scripts/data_quality_report.py`, `scripts/run_evaluation.py` and
`scripts/train_export_pipeline.py` read those two files. Notebooks 01 and 03 write the same two
files with the same library calls, and display the checks this script leaves out.

The employee identifier is replaced by an HMAC-SHA256 digest under `ANONYMIZATION_KEY`, which
is read from the environment. The key changes the digests, and the scripts that follow read the
digest column without using its values.
"""

from __future__ import annotations

import sys

from attrition_serving.config import PATHS
from attrition_serving.data.frames import write_frames
from attrition_serving.data.source import EXTRACT_FILES
from attrition_serving.utils.paths import rel

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    missing = [name for name in EXTRACT_FILES.values() if not (PATHS.data_raw / name).exists()]
    if missing:
        print(
            f"[fail] no {', '.join(missing)} under {rel(PATHS.data_raw)}. Rebuild the extracts "
            "with `uv run python scripts/build_extracts.py --source <IBM csv>`; "
            "docs/data-source.md says what that file is.",
            file=sys.stderr,
        )
        return 1

    frames = write_frames(PATHS.data_raw, PATHS.data_processed)
    for name, frame in frames.items():
        print(
            f"[ok] {rel(PATHS.data_processed / name)} — "
            f"{len(frame):,} rows, {frame.shape[1]} columns"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
