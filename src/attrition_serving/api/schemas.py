from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

Primitive = int | float | str | bool | None


class PredictRequest(BaseModel):
    """
    Requête flexible mais validée :
    - features = dict[str, primitive]
    """

    features: Dict[str, Primitive] = Field(..., description="Features brutes (avant encodage).")

    @field_validator("features")
    @classmethod
    def validate_primitives(cls, v: Dict[str, Any]) -> Dict[str, Primitive]:
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
    db_id: Optional[int] = None


class HistoryItem(BaseModel):
    id: int
    created_at: str
    employee_id: Optional[int]
    proba_depart: float
    prediction: int
    threshold: float
    model_version: str
    input_payload: Dict[str, Any]
