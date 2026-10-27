# Operating the service

The schema and the decision log are described in [`DB.md`](DB.md), and the numbers behind the
threshold in [`protocol.md`](protocol.md).

## Bringing it up

```bash
uv sync --group dev --group db --group serve
cp .env.example .env.local          # set API_KEY; leave MODEL_THRESHOLD unset
docker compose up -d                # PostgreSQL on 5432
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
uv run uvicorn attrition_serving.api.main:app --port 8000
```

Swagger is then served on `http://localhost:8000/docs`, and `/` redirects there. The page is
generated from the Pydantic models in the code. It shows the response in full, while the request
model only states that `features` maps names to simple values. The 32 required names are listed
in `models/expected_features.json`, and the service checks every prediction request against
them.

**Leave `MODEL_THRESHOLD` unset** unless you intend to override the threshold recorded in
`models/model_card.json`. The variable used to be set to 0.5, a value that no analysis
justified, and the service applied it.

## The routes

| Route | What it answers | Key |
|---|---|---|
| `GET /health` | the process is alive; reads neither the model nor the database | no |
| `POST /predict` | probability, decision, and the threshold used, for a full payload | yes |
| `POST /predict_by_id/{id}` | the same, for an employee already in `employees` | yes |
| `GET /history` | the latest decisions, most recent first, 50 unless `limit` says otherwise | yes |
| `GET /history/{id}` | the decisions recorded for one employee, most recent first, 50 by default | yes |

`/health` needs no key, so a health check does not depend on a secret.

The features are sent inside a `features` object. Ten complete payloads are in
`tests/fixtures/employees_sample.json`, and the shortest way to send one is:

```bash
python -c "import json; s=json.load(open('tests/fixtures/employees_sample.json')); print(json.dumps({'features': s[0]}))" > one.json
curl -s localhost:8000/predict -H "X-API-Key: $API_KEY" \
     -H 'Content-Type: application/json' -d @one.json
```

The answer has six fields:

```json
{"proba_depart": 0.52, "prediction": 1, "threshold": 0.1105,
 "model_version": "local-dev", "stored": true, "db_id": 5}
```

`threshold` and `model_version` record which threshold and which model produced the decision.
`stored` says whether the decision reached the database, and `db_id` is the id of its row.
Logging is best-effort. The route answers whether or not the log accepts the row, so
`stored: false` on an otherwise successful `/predict` means that the log is failing without
any error status.

### What each error code means

- `401`: the `X-API-Key` header is missing or does not match.
- `404`: `/predict_by_id` received an id that is not in `employees`.
- `422`: the JSON is malformed, the payload is not wrapped in `features`, a value has an
  unsupported type, or expected features are missing or null. For missing and null features, the
  body lists all of them in a single answer.
- `500`: the configuration is incomplete (no `API_KEY`, no `DATABASE_URL`, or no threshold), the
  model artefact is missing, a route that reads the database (`/predict_by_id`, `/history`)
  cannot reach it, or the features stored for an employee do not match the contract. A failed
  write to the decision log does not cause a `500`, and the answer carries `stored: false`.

## In a container

```bash
docker build -t attrition-api .
docker run -d --name attrition_api --env-file .env.docker -p 7860:7860 attrition-api
```

The env file must provide `API_KEY` and `DATABASE_URL`, and should set `MODEL_VERSION`, which
otherwise defaults to `dev`. The image contains the package, its locked dependencies and
`models/`. The scripts, the SQL files and the fixtures are not copied, so applying the schema
and seeding the table are done from a checkout. The image runs as uid 1000 and listens on port
7860. Its `HEALTHCHECK` calls `/health`, which needs neither the artefact nor the database, so a
healthy status only means that the process is alive.

A Hugging Face Docker Space expects uid 1000 and port 7860. A Space whose card declares
`sdk: docker` and `app_port: 7860` builds this Dockerfile unchanged, with `API_KEY`,
`DATABASE_URL` and `MODEL_VERSION` set as the Space's secrets. Locally, `docker compose up`
starts PostgreSQL only, and the service runs either with uvicorn, as in the first section, or
in the container above.

A managed PostgreSQL usually requires TLS. The service passes `DATABASE_URL` to SQLAlchemy
unchanged, so the URL has to include `sslmode=require`:

```
DATABASE_URL=postgresql+psycopg://postgres:<password>@db.<ref>.<host>:5432/postgres?sslmode=require
```

The database scripts under `scripts/` add that parameter themselves for hosts under
`supabase.co`.

## The CI workflow

The CI workflow is started by hand from the Actions tab. It runs `uv sync --frozen`,
`ruff check`, `ruff format --check` and `bandit -c pyproject.toml`, applies the schema, seeds
the ten employees, and then runs `pytest` against a PostgreSQL service container, so the
integration tier runs. `SKIP_DOTENV=1` is set, so a stray `.env` file on a runner cannot change
the configuration that the tests read.

`MODEL_VERSION` comes from the environment and is written into every row of `predictions`. The
CI workflow sets it to `ci` and `.env.example` sets it to `local-dev`. When it is unset, the
service uses `dev`, since the model card has no version field. Together with `threshold`, also
stored in each row, the version allows a past decision to be explained. Rolling back
therefore means redeploying an earlier tagged release, such as `v1.0.0`, with `MODEL_VERSION`
set to match it. If the version string is left unchanged, every row written afterwards names
the wrong model.

## Secrets

No secret is committed. `.env.local` and `.env.docker` are ignored by git, and the CI workflow
and any deployment set their own values.

| Variable | What leaking it costs |
|---|---|
| `API_KEY` | anyone can score against the model and write to the decision log |
| `DATABASE_URL` | direct read and write on the decision log, payloads included |
| `ANONYMIZATION_KEY` | the HMAC key: an anonymised employee id becomes reversible by trying candidates |

`.env.example` lists the variables with placeholder or local-development values and leaves
`MODEL_THRESHOLD` empty. It is the file the setup says to copy, so copying it keeps the
threshold recorded in the model card, and overriding that threshold requires an explicit
change.

The person who runs the service chooses all three values. A long random string serves for
`API_KEY` and `ANONYMIZATION_KEY` (`python -c "import secrets; print(secrets.token_hex(32))"`),
and `DATABASE_URL` comes from the database, local or managed. The service itself does not read
`ANONYMIZATION_KEY`, which `scripts/build_frames.py` and notebook 01 use when they build the
joined frame. That key should be chosen once and kept, since a new key gives every employee a
new anonymised id.

### Known gaps in protection

- No rate limiting. A valid key can be used as fast as the service answers.
- No TLS locally. uvicorn serves plain HTTP, so the header carrying the key travels in clear.
- No key rotation. There is one key, changed by hand.
- No audit of reads. `/history` returns decisions and keeps no record of the request.
- No caller identity. The log records what was decided and has no column for who asked.

These gaps are acceptable for an archived demonstration. Each of them would have to be closed
before a similar service handled real HR data.

The decision log holds the same personal fields as the request: age, department, job title,
salary, marital status and tenure. On this dataset those fields describe no real person
([`data-source.md`](data-source.md)). With a real extract, the table would fall under the same
data-protection rules as its source, and it would have to be handled with more care than
ordinary application logs.

## Troubleshooting

Work through the steps in order. Each step either gives a diagnosis or leads to the next one.

### 1. Check that the process is up

```bash
curl -s localhost:8000/health
```

A 200 means only that the process is alive. No answer means the process is down, and the logs
of step 6 say why.

### 2. Check the threshold the service applies

This failure reached production once, so it is checked second.

```bash
curl -s localhost:8000/predict -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' -d @one.json \
  | python -c "import json,sys; d=json.load(sys.stdin); print(d['threshold'], d['model_version'])"

python -c "import json; print(json.load(open('models/model_card.json'))['default_threshold'])"
```

The two values must agree. If they differ, something overrides the card. Check
`MODEL_THRESHOLD` in the process environment, and in `.env.local` if one is loaded.
`uv run pytest --no-cov tests/unit/api/test_served_threshold.py` checks the same agreement without a
running service.

### 3. Check the scale of the probabilities

`proba_depart` is calibrated, so 0.1 means about one departure in ten. Over the
cross-validation, the mean predicted risk of the shipped arm was 0.163 against a base rate of
0.161 (`reports/evaluation_summary.json`). If the mean over recent traffic is far from that
value, the traffic does not come from the population the model was fitted on. This is the
drift signal that the repository does not monitor, and it can be computed before any departure
has been observed.

If the decision looks wrong while the probability looks right, the threshold is the cause, and
step 2 checks it.

### 4. Check the model version

Every prediction and every `/history` row carries its `model_version`. A version of `dev` in
production means that `MODEL_VERSION` was not set.

The artefact is a pickle, and a pickle may fail to load, or behave differently, under another
version of the library that wrote it. The model card records that version, so one command
compares it with the installed one:

```bash
python -c "import sklearn, json; c=json.load(open('models/model_card.json')); print('card', c['sklearn_version'], '| here', sklearn.__version__)"
```

### 5. Check that decisions are being logged

```bash
docker exec -it attrition_postgres psql -U attrition -d attrition_serving \
  -c "SELECT created_at, proba_depart, prediction, threshold, model_version
      FROM predictions ORDER BY created_at DESC LIMIT 5;"

docker compose ps
uv run python scripts/db_smoke_test.py     # connectivity and row counts
uv run python scripts/db_run_checks.py     # replays the inspection queries
```

### 6. Read the logs

uvicorn writes its log to the terminal it runs in. For the container, the log is read with:

```bash
docker logs -f attrition_api
```

The service adds no request identifier, so a failed request is found in the log by its time
and its route.

### 7. Start from a clean state

Run the six commands at the top of this page, in that order.
