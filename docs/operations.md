# Operating the service — routes, deployment, secrets, and what to check when it answers badly

The schema and the decision log are in [`DB.md`](DB.md); the numbers the service decides with
are in [`protocol.md`](protocol.md).

## Bringing it up

```bash
uv sync --group dev --group db --group serve
cp .env.example .env.local          # set API_KEY; leave MODEL_THRESHOLD unset
docker compose up -d                # PostgreSQL on 5432
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
uv run uvicorn attrition_serving.api.main:app --port 8000
```

Swagger is then on `http://localhost:8000/docs`, and it is the reference for the request and
response shapes: they are Pydantic models, so the generated page cannot drift from the code.

**Leave `MODEL_THRESHOLD` unset** unless you mean to override the operating point recorded in
`models/model_card.json`. That variable used to be set to a value nothing justified, and the
service decided at it.

## The routes

| Route | What it answers | Key |
|---|---|---|
| `GET /health` | the process is alive; touches neither model nor database | no |
| `POST /predict` | probability, decision, and the threshold used, for a full payload | yes |
| `POST /predict_by_id/{id}` | the same, for an employee already in `employees` | yes |
| `GET /history` | what was decided lately, most recent first | yes |
| `GET /history/{id}` | every decision recorded for one employee | yes |

`/health` is open because a health check that needs a secret fails for the wrong reason.

The features go **under a `features` key**, not at the top level. Ten complete payloads are in
`tests/fixtures/employees_sample.json`; the shortest way to send one:

```bash
python -c "import json; s=json.load(open('tests/fixtures/employees_sample.json')); print(json.dumps({'features': s[0]}))" > one.json
curl -s localhost:8000/predict -H "X-API-Key: $API_KEY" \
     -H 'Content-Type: application/json' -d @one.json
```

The answer carries six fields, and the last two are the ones worth reading:

```json
{"proba_depart": 0.52, "prediction": 1, "threshold": 0.1105,
 "model_version": "local-dev", "stored": true, "db_id": 5}
```

`stored` says whether the decision reached the database. Predictions are logged on a
best-effort basis: the route answers whether or not the log accepts the row, so
`stored: false` on a healthy `/predict` is the signal that the log is failing silently.

### What each error code means

- `401` — the `X-API-Key` header is missing, or does not match.
- `422` — the JSON is malformed, or the payload is not wrapped under `features`. The body
  names every field it is missing, not one per round trip.
- `500` — the model artefact is missing, or the service was asked for an employee the
  database cannot be read for. A decision log that is down does not produce one: the write
  is best-effort, and the answer says `stored: false`.

## In a container

```bash
docker build -t attrition-api .
docker run -d --name attrition_api --env-file .env.docker -p 7860:7860 attrition-api
```

The env file carries at least `API_KEY`, `DATABASE_URL` and `MODEL_VERSION`. The image holds
the code and `models/`, and stops there. Applying the schema, seeding the table and holding
the request fixtures are all things an operator does from a checkout. It runs as uid 1000, and its
`HEALTHCHECK` calls `/health`, chosen because it needs neither the artefact nor the database:
an orchestrator gets an answer that means the process is alive and nothing more.

The hosted deployment this was built for has been decommissioned, along with the managed
database it wrote to. `docker compose up` brings the local equivalent back.

A managed PostgreSQL usually wants TLS:

```
DATABASE_URL=postgresql+psycopg://postgres:<password>@db.<ref>.<host>:5432/postgres?sslmode=require
```

## The pipeline

On every push and pull request: `uv sync --frozen`, `ruff check`, `ruff format --check`,
`bandit -c pyproject.toml`, then `pytest` against a real PostgreSQL service container, so the
integration tier runs instead of skipping. `SKIP_DOTENV=1` is set, so a stray `.env` on a
runner cannot change what the tests read.

`MODEL_VERSION` is written into every row of `predictions`: `v1.0.0` on a tagged release,
`main-<sha>` in CI. Together with `threshold`, also logged per row, that is what makes a past
decision explainable. Rolling back means redeploying a previous tag and keeping
`MODEL_VERSION` consistent with it — a rollback that leaves the version string behind makes
the log say the wrong thing about every row it writes afterwards.

## Secrets

Nothing sensitive is committed. `.env.local` and `.env.docker` are ignored, and the CI and any
deployment target inject their own values.

| Variable | What leaking it costs |
|---|---|
| `API_KEY` | anyone can score against the model and write to the decision log |
| `DATABASE_URL` | direct read and write on the decision log, payloads included |
| `ANONYMIZATION_KEY` | the HMAC key: an anonymised employee id becomes reversible by trying candidates |

`.env.example` carries the names and no values. It is also the file the setup tells you to
copy, so it is deliberately silent about the threshold: overriding the model card's operating
point has to be a decision, not an inheritance.

### What is not protected

- **No rate limiting.** A valid key can be used as fast as the service answers.
- **No TLS locally.** `docker compose` serves plain HTTP, and the header carrying the key is
  in clear on the wire.
- **No key rotation.** One key, changed by hand.
- **No audit of reads.** `/history` returns decisions and records nothing about having done so.
- **No per-caller identity.** The log says what was decided, never by whom.

None of these matter for an archived demonstration. All of them would have to be answered
before anything like it went near a real HR system.

The decision log holds the same personal fields the request did — age, department, job title,
salary, marital status, tenure. On this dataset those fields describe nobody
([`data-source.md`](data-source.md)), but the table would fall under the same handling rules
as its source the day it held a real extract, and treating it as ordinary application logging
would be a mistake.

## When it answers badly

In order. Each step gives a verdict or hands you to the next.

### 1. Is it up, or up and wrong?

```bash
curl -s localhost:8000/health
```

A 200 means the process is alive and nothing more. No answer means the process is down: go to
the logs.

### 2. Does it decide at the threshold it claims?

This is the failure that once shipped, so it comes second and not last.

```bash
curl -s localhost:8000/predict -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' -d @one.json \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['threshold'], d['model_version'])"

python -c "import json; print(json.load(open('models/model_card.json'))['default_threshold'])"
```

The two must agree. If they do not, something is overriding the card: check `MODEL_THRESHOLD`
in the process environment, and in `.env.local` if one is loaded.
`uv run pytest tests/unit/test_served_threshold_matches_artifact.py` asserts the same thing
without a running service.

### 3. Are the answers wrong, or just unexpected?

`proba_depart` is calibrated: 0.1 means about one departure in ten. The model was scored at a
mean predicted risk of 0.163 against a base rate of 0.161
(`reports/evaluation_summary.json`). A mean well away from that says the traffic is not the
population the model was fitted on — which is the drift signal nothing here watches, and the
earliest one available, since it arrives long before any label does.

If the *decision* looks wrong while the probability looks right, it is the threshold, and step
2 settles it.

### 4. Is the model the one you think?

Every prediction and every `/history` row carries its `model_version`. A version of `dev` in
production means nothing set it.

The artefact is a pickle, and pickles travel badly between library versions. The card records
which one wrote it, so the comparison is one command:

```bash
python -c "import sklearn, json; c=json.load(open('models/model_card.json')); print('card', c['sklearn_version'], '| here', sklearn.__version__)"
```

### 5. Is anything being written down?

```bash
docker exec -it attrition_postgres psql -U attrition -d attrition_serving \
  -c "SELECT created_at, proba_depart, prediction, threshold, model_version
      FROM predictions ORDER BY created_at DESC LIMIT 5;"

docker compose ps
uv run python scripts/db_smoke_test.py     # connectivity and row counts
uv run python scripts/db_run_checks.py     # replays the inspection queries
```

### 6. The logs

```bash
docker compose logs -f api
```

Every request carries a request id, echoed in the `x-request-id` response header, so a
caller's failed request is found by that id and not by timestamp.

### 7. Starting from nothing

The five commands at the top of this page, in that order.
