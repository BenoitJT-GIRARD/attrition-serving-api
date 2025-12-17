from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Literal

import pandas as pd

from attrition_serving.config import SETTINGS


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    return pd.read_csv(path, encoding="utf-8", sep=",", low_memory=False)


def parse_eval_number(series: pd.Series) -> pd.Series:
    # "E_1" -> 1
    return series.astype(str).str.strip().str.replace("E_", "", regex=False).astype("Int64")


def anonymize_employee_id(
    series: pd.Series,
    key: str | None = None,
    prefix: str = "emp_",
) -> pd.Series:
    """
    Stable anonymization using HMAC-SHA256.
    Non reversible without key.
    """
    secret = key or SETTINGS.anonymization_key
    if not secret:
        raise ValueError("Missing anonymization key. Set ANONYMIZATION_KEY in .env")

    secret_bytes = secret.encode("utf-8")

    def _hmac(x: object) -> str:
        msg = str(x).encode("utf-8")
        digest = hmac.new(secret_bytes, msg, hashlib.sha256).hexdigest()
        return f"{prefix}{digest[:16]}"  # short stable id

    return series.apply(_hmac)


def load_sirh(path: Path) -> pd.DataFrame:
    df = _read_csv(path)
    # Expected join key already numeric: id_employee
    if "id_employee" not in df.columns:
        raise KeyError("sirh: missing column 'id_employee'")
    return df


def load_eval(path: Path) -> pd.DataFrame:
    df = _read_csv(path)
    if "eval_number" not in df.columns:
        raise KeyError("eval: missing column 'eval_number'")
    df["eval_number_int"] = parse_eval_number(df["eval_number"])
    return df


def load_sondage(path: Path) -> pd.DataFrame:
    df = _read_csv(path)
    if "code_sondage" not in df.columns:
        raise KeyError("sondage: missing column 'code_sondage'")
    return df


def check_duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> pd.DataFrame:
    dup = df[df.duplicated(subset=subset, keep=False)].copy()
    return dup


def join_sources(
    sirh: pd.DataFrame,
    eval_df: pd.DataFrame,
    sondage: pd.DataFrame,
    how: Literal["inner", "left"] = "inner",
) -> pd.DataFrame:
    """
    Join strategy:
    - Map eval_number_int <-> id_employee and code_sondage <-> id_employee
      (assumption based on your mapping; if needed we'll adapt after inspecting CSVs)
    """
    if "eval_number_int" not in eval_df.columns:
        raise KeyError("eval_df missing 'eval_number_int' (run load_eval)")

    df = sirh.merge(eval_df, left_on="id_employee", right_on="eval_number_int", how=how)
    df = df.merge(sondage, left_on="id_employee", right_on="code_sondage", how=how)
    return df
