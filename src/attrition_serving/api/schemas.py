from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

Primitive = int | float | str | bool | None


class PredictRequest(BaseModel):
    """
    Requête flexible mais validée :
    - features = dict[str, primitive]
    """

    features: dict[str, Primitive] = Field(..., description="Features brutes (avant encodage).")

    @field_validator("features")
    @classmethod
    def validate_primitives(cls, v: dict[str, Any]) -> dict[str, Primitive]:
        for k, val in v.items():
            if not isinstance(val, (int, float, str, bool)) and val is not None:
                raise ValueError(f"Valeur non supportée pour {k}: {type(val)}")
        return v


class PredictResponse(BaseModel):
    proba_depart: float
    prediction: int
    threshold: float
    model_version: str
    stored: bool
    db_id: int | None = None


class HistoryItem(BaseModel):
    id: int
    created_at: str
    employee_id: int | None
    proba_depart: float
    prediction: int
    threshold: float
    model_version: str
    input_payload: dict[str, Any]
