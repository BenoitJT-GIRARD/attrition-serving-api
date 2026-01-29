from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
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


@router.post("/predict", response_model=PredictResponse, dependencies=[Depends(require_api_key)])
def predict(req: PredictRequest, db: Session = Depends(get_db)):
    cfg = get_config()

    payload = normalize_payload(req.features)
    missing, nulls = check_payload(payload)

    # On refuse les payloads incomplets -> 422 explicite (propre pour l’évaluation)
    if missing or nulls:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Payload incomplet ou valeurs nulles. Fournis toutes les features attendues.",
                "missing_features": missing,
                "null_features": nulls,
                "hint": "Utilise un record complet depuis data/processed/api_test/X_test_sample.json",
            },
        )

    proba = predict_proba(payload)
    pred = decide(proba)

    input_json = json.dumps(payload, ensure_ascii=False)
    row = db.execute(
        _INSERT_PRED,
        {
            "employee_id": None,
            "input_payload": input_json,
            "proba": proba,
            "pred": pred,
            "thr": cfg.model_threshold,
            "ver": cfg.model_version,
        },
    ).fetchone()
    db.commit()

    return PredictResponse(
        proba_depart=proba,
        prediction=pred,
        threshold=cfg.model_threshold,
        model_version=cfg.model_version,
        stored=True,
        db_id=int(row[0]),
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
    # selon driver/param, ça peut arriver en dict OU en string JSON
    if isinstance(payload, str):
        payload = json.loads(payload)

    payload = normalize_payload(payload)
    missing, nulls = check_payload(payload)
    if missing or nulls:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Features en DB incohérentes avec expected_features.json (seed à vérifier).",
                "missing_features": missing,
                "null_features": nulls,
            },
        )

    proba = predict_proba(payload)
    pred = decide(proba)

    input_json = json.dumps(payload, ensure_ascii=False)
    row2 = db.execute(
        _INSERT_PRED,
        {
            "employee_id": employee_id,
            "input_payload": input_json,
            "proba": proba,
            "pred": pred,
            "thr": cfg.model_threshold,
            "ver": cfg.model_version,
        },
    ).fetchone()
    db.commit()

    return PredictResponse(
        proba_depart=proba,
        prediction=pred,
        threshold=cfg.model_threshold,
        model_version=cfg.model_version,
        stored=True,
        db_id=int(row2[0]),
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
