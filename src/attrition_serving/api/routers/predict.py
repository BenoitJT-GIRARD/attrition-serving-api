"""The five routes: health, two ways to score, and two ways to read the log back.

Logging a prediction is best-effort on purpose. A database that is down should not stop the
service from answering -- but it does mean an empty log with a healthy `/predict` is a
silent failure, and the runbook says where to look.

`/predict_by_id` reads the features from `employees` so a caller can send an id instead of
thirty-two fields; `/history` and `/history/{employee_id}` return what was decided, with
the threshold and the model version that decided it.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from attrition_serving.api.deps import get_db, require_api_key
from attrition_serving.api.schemas import HistoryItem, PredictRequest, PredictResponse
from attrition_serving.api.service import check_payload, decide, normalize_payload, predict_proba
from attrition_serving.api.settings import get_config

router = APIRouter(tags=["prediction"])


@router.get("/health")
def health():
    return {"status": "ok"}


_INSERT_PRED = text("""
    INSERT INTO predictions (employee_id, input_payload, proba_depart, prediction, threshold, model_version)
    VALUES (:employee_id, CAST(:input_payload AS JSONB), :proba, :pred, :thr, :ver)
    RETURNING id
""")


def _log_decision(db: Session, **row) -> int | None:
    """Write the decision, or say it was not written. Never raise.

    The module docstring has always said the log is best-effort. It was not: the insert ran
    unguarded, so a database that was down turned every `/predict` into a 500 -- the opposite
    of what the documentation promised, and what the system tier found by starting the
    service without one. `stored` in the response is how a caller learns the difference.
    """
    try:
        written = db.execute(_INSERT_PRED, row).fetchone()
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        return None
    return int(written[0])


@router.post("/predict", response_model=PredictResponse, dependencies=[Depends(require_api_key)])
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    cfg = get_config()

    payload = normalize_payload(req.features)
    missing, nulls = check_payload(payload)

    # An incomplete payload is refused rather than filled in. Imputing a missing
    # feature at serving time silently changes what was scored.
    if missing or nulls:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Incomplete payload or null values: every expected feature is required.",
                "missing_features": missing,
                "null_features": nulls,
                "hint": "Send a complete record; tests/fixtures/employees_sample.json holds ten.",
            },
        )

    proba = predict_proba(payload)
    pred = decide(proba)

    db_id = _log_decision(
        db,
        employee_id=None,
        input_payload=json.dumps(payload, ensure_ascii=False),
        proba=proba,
        pred=pred,
        thr=cfg.model_threshold,
        ver=cfg.model_version,
    )

    return PredictResponse(
        proba_depart=proba,
        prediction=pred,
        threshold=cfg.model_threshold,
        model_version=cfg.model_version,
        stored=db_id is not None,
        db_id=db_id,
    )


@router.post(
    "/predict_by_id/{employee_id}",
    response_model=PredictResponse,
    dependencies=[Depends(require_api_key)],
)
def predict_by_id(employee_id: int, db: Session = Depends(get_db)):
    cfg = get_config()

    q_emp = text("SELECT features FROM employees WHERE employee_id = :id")
    row = db.execute(q_emp, {"id": employee_id}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")

    payload = row[0]
    # JSONB comes back as a dict from psycopg and as a JSON string from some drivers.
    if isinstance(payload, str):
        payload = json.loads(payload)

    payload = normalize_payload(payload)
    missing, nulls = check_payload(payload)
    if missing or nulls:
        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "The features stored for this employee do not match "
                    "expected_features.json. Re-run the seed script."
                ),
                "missing_features": missing,
                "null_features": nulls,
            },
        )

    proba = predict_proba(payload)
    pred = decide(proba)

    db_id = _log_decision(
        db,
        employee_id=employee_id,
        input_payload=json.dumps(payload, ensure_ascii=False),
        proba=proba,
        pred=pred,
        thr=cfg.model_threshold,
        ver=cfg.model_version,
    )

    return PredictResponse(
        proba_depart=proba,
        prediction=pred,
        threshold=cfg.model_threshold,
        model_version=cfg.model_version,
        stored=db_id is not None,
        db_id=db_id,
    )


@router.get("/history", response_model=list[HistoryItem], dependencies=[Depends(require_api_key)])
def history(limit: int = 50, db: Session = Depends(get_db)):
    q = text("""
        SELECT id, created_at, employee_id, proba_depart, prediction, threshold, model_version, input_payload
        FROM predictions
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    rows = db.execute(q, {"limit": limit}).fetchall()
    return [
        HistoryItem(
            id=int(r[0]),
            created_at=r[1].isoformat(),
            employee_id=r[2],
            proba_depart=float(r[3]),
            prediction=int(r[4]),
            threshold=float(r[5]),
            model_version=r[6],
            input_payload=r[7] if isinstance(r[7], dict) else json.loads(r[7]),
        )
        for r in rows
    ]


@router.get(
    "/history/{employee_id}",
    response_model=list[HistoryItem],
    dependencies=[Depends(require_api_key)],
)
def history_by_id(employee_id: int, limit: int = 50, db: Session = Depends(get_db)):
    q = text("""
        SELECT id, created_at, employee_id, proba_depart, prediction, threshold, model_version, input_payload
        FROM predictions
        WHERE employee_id = :employee_id
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    rows = db.execute(q, {"employee_id": employee_id, "limit": limit}).fetchall()
    return [
        HistoryItem(
            id=int(r[0]),
            created_at=r[1].isoformat(),
            employee_id=r[2],
            proba_depart=float(r[3]),
            prediction=int(r[4]),
            threshold=float(r[5]),
            model_version=r[6],
            input_payload=r[7] if isinstance(r[7], dict) else json.loads(r[7]),
        )
        for r in rows
    ]
