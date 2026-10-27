"""The two frames under `data/processed/`, built from the three extracts.

Notebook 01 joins the extracts and replaces the employee identifier with its keyed digest.
Notebook 03 reads the joined frame back and derives the features. Both notebooks display their
checks along the way. This module makes the same library calls in the same order, so that
`scripts/build_frames.py` can write both frames on a fresh clone without executing a notebook.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from attrition_serving.data.features import add_engineered_features
from attrition_serving.data.io import (
    anonymize_employee_id,
    join_sources,
    load_eval,
    load_sirh,
    load_sondage,
)
from attrition_serving.data.source import EXTRACT_FILES

#: The file notebook 01 writes, and the file notebook 03 writes from it.
JOINED_FILE = "employees_joined.parquet"
FEATURES_FILE = "employees_features.parquet"


def build_joined(raw_dir: Path, key: str | None = None) -> pd.DataFrame:
    """The inner join of the three extracts, with `id_employee` replaced by its digest.

    The digest is the one `io.anonymize_employee_id` computes, under `key` or, when no key is
    given, under `ANONYMIZATION_KEY`.
    """
    joined = join_sources(
        load_sirh(raw_dir / EXTRACT_FILES["sirh"]),
        load_eval(raw_dir / EXTRACT_FILES["eval"]),
        load_sondage(raw_dir / EXTRACT_FILES["sondage"]),
        how="inner",
    )
    joined["employee_id_anon"] = anonymize_employee_id(joined["id_employee"], key=key)
    return joined.drop(columns=["id_employee"])


def write_frames(
    raw_dir: Path, processed_dir: Path, key: str | None = None
) -> dict[str, pd.DataFrame]:
    """Write the joined frame, read it back, then derive and write the feature frame.

    The features are derived from the joined frame as Parquet returns it, because that is the
    frame notebook 03 reads. Returns both frames, keyed by file name.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    joined_path = processed_dir / JOINED_FILE
    build_joined(raw_dir, key=key).to_parquet(joined_path, index=False)

    joined = pd.read_parquet(joined_path)
    featured = add_engineered_features(joined)
    featured.to_parquet(processed_dir / FEATURES_FILE, index=False)
    return {JOINED_FILE: joined, FEATURES_FILE: featured}
