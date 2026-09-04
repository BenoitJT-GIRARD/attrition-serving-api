# Runbook — when the service answers badly

In order. Each step either produces a verdict or hands you to the next one.

## 1. Is it up, or is it up and wrong?

```bash
curl -s localhost:8000/health
```

`/health` needs no key and touches neither the model nor the database, so a 200 here means
the process is alive and nothing more. If it does not answer, the process is down: go to
[the logs](#6-the-logs).

## 2. Does it decide at the threshold it claims?

This is the failure that once shipped, so it is the second thing to check rather than the
last. The service reads `default_threshold` from the model card unless `MODEL_THRESHOLD`
overrides it, and a prediction returns the threshold it used:

```bash
# one employee out of the ten committed fixtures, wrapped as the route expects
python -c "import json; s=json.load(open('data/processed/api_test/X_test_sample.json')); print(json.dumps({'features': s[0]}))" > one.json

curl -s localhost:8000/predict -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' -d @one.json \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['threshold'], d['model_version'])"

python -c "import json; print(json.load(open('models/model_card.json'))['default_threshold'])"
```

The threshold the service reports and the one the card declares must agree. If they do not,
an environment variable is overriding the card — check
`MODEL_THRESHOLD` in the process environment, and in `.env.local` if one is loaded. A
service that refuses to start is the intended behaviour when the card carries no threshold
at all: serving an undocumented operating point is worse than not serving.

`uv run pytest tests/unit/test_served_threshold_matches_artifact.py` asserts the same thing
without a running service.

## 3. Are the answers wrong, or just unexpected?

`proba_depart` is calibrated: a value of 0.1 means about one departure in ten. If the
distribution of returned probabilities looks shifted, compare it against what the model was
scored on — mean predicted risk 0.163 against a base rate of 0.161, in
`reports/evaluation_summary.json`. A mean well away from that means the traffic is not the
population the model was fit on, not that the model broke.

If the *decision* looks wrong while the probability looks right, it is the threshold, and
step 2 is where that is settled.

## 4. Is the model the one you think?

Every prediction carries its `model_version`, and so does every row of `/history`. It comes
from `MODEL_VERSION` when that is set and from the model card otherwise, so a version of
`dev` in production means nothing set it.

If the service failed to load the model at all, the first suspect is the library rather
than the file: a scikit-learn pickle is only readable by a compatible scikit-learn, and the
card records the version that wrote it.

```bash
python -c "import sklearn, json; c=json.load(open('models/model_card.json')); print('card', c['sklearn_version'], '| here', sklearn.__version__)"
```

## 5. Is anything being written down?

```bash
docker exec -it attrition_postgres psql -U attrition -d attrition_serving \
  -c "SELECT created_at, proba_depart, prediction, threshold, model_version
      FROM predictions ORDER BY created_at DESC LIMIT 5;"
```

Predictions are logged on a best-effort basis: a database that is down does not stop the
service from answering, by design. So an empty table with a healthy `/predict` means the
log write is failing silently — check `DATABASE_URL` and the container.

```bash
docker compose ps
uv run python scripts/db_smoke_test.py     # connectivity and row counts
uv run python scripts/db_run_checks.py     # replays the inspection queries
```

## 6. The logs

```bash
docker compose logs -f api        # containerised
```

Every request carries a request id, echoed in the `x-request-id` response header, so a
caller's failed request can be found by that id rather than by timestamp.

## 7. Starting from nothing

```bash
docker compose up -d                                # PostgreSQL
uv run python scripts/db_apply_schema.py            # idempotent
uv run python scripts/db_seed_employees.py          # the ten request fixtures
uv run uvicorn attrition_serving.api.main:app --port 8000
```

## What is not monitored

There is no drift detection and no alerting. This is an archived project: the runbook above
is what a person does when they look, and nothing looks on its own. A service kept in
production would need the predicted-probability distribution watched against the figure in
step 3, which is the earliest signal available and arrives long before any label does.
