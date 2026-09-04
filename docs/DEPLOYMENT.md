# Deployment — local, container, hosted, and the CI in between

## What this covers

Serving a frozen model behind FastAPI, with a PostgreSQL backend for the decision log,
secrets that never enter git, and a pipeline that tests before it deploys.

---

## Three environments

### Local

- API on `localhost:8000`
- PostgreSQL through `docker compose`, on `localhost:5432`
- Configuration in `.env.local`, which is not committed

### CI

- an ephemeral PostgreSQL service container
- configuration injected as workflow variables, never from a file
- `SKIP_DOTENV=1`, so a stray `.env` on a runner cannot change what the tests read

### Hosted

- the container, serving on port `7860`
- a managed PostgreSQL
- secrets held by the host, not by the image

---

## Locally

### 1) Dependencies

```bash
uv sync --group dev --group db --group serve
```

### 2) Configuration

```bash
cp .env.example .env.local
```

Set `API_KEY`. **Leave `MODEL_THRESHOLD` unset** unless you mean to override the operating
point recorded in `models/model_card.json` — that variable used to be set to a value nothing
justified, and the service decided at it.

### 3) Database

```bash
docker compose up -d
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
```

### 4) API

```bash
uv run uvicorn attrition_serving.api.main:app --reload --port 8000
```

### 5) Swagger

- http://localhost:8000/docs

---

## In a container

### Build

```bash
docker build -t attrition-api .
```

### Run, on port 7860

Create an env file — `.env.docker` — carrying at least `API_KEY`, `DATABASE_URL` and
`MODEL_VERSION`:

```bash
docker run -d --name attrition_api \
  --env-file .env.docker \
  -p 7860:7860 \
  attrition-api
```

- http://localhost:7860/docs

---

## On a Docker-based host

### 1) The Space

Create a Docker Space and connect the repository, or push to it from a workflow. The host
reads this repository's `README.md` front-matter:

```
sdk: docker
app_port: 7860
```

### 2) Secrets

In the Space settings: `DATABASE_URL`, `API_KEY`, `MODEL_VERSION`.

### 3) Check it came up

- the container starts without an error in its log;
- `/docs` answers;
- a `/predict` call returns 200 with a key and 401 without one;
- a row appears in `predictions`.

That last one is the check that matters. The first three can pass on a service whose
database is unreachable, because the model loads and scores regardless — and a prediction
that is not logged is, for this repository, a prediction that did not happen.

---

## CI/CD

### Branches

- `main` is what deploys;
- `feature/*` and `fix/*` are where work happens;
- releases are tagged `vX.Y.Z`.

### On every push and pull request

- checkout, `uv sync`
- `ruff check` and `ruff format --check`
- `bandit`
- `pytest`, with a PostgreSQL service container so the integration tests actually run

### On a push to `main`

- deploy to the Space.

### Secrets

In the repository settings, under Actions: `HF_TOKEN` and `HF_SPACE`.

### The database in CI

The integration tests need PostgreSQL. CI starts a service container and points
`DATABASE_URL` at it. Without one they skip in three seconds and say so, rather than hanging
until a connection times out.

---

## Versioning

`MODEL_VERSION` is written into every row of `predictions`, so a decision can be traced to
the model that made it.

- `MODEL_VERSION=v1.0.0` on a tagged release
- `MODEL_VERSION=main-<sha>` in CI

Together with `threshold`, also logged per row, this is what makes a past decision
explainable. A probability without the model version and the threshold that turned it into a
decision records nothing usable.

---

## Rollback

Redeploy a previous tag, or push a known-good commit to `main`. Keep `MODEL_VERSION`
consistent with what is deployed — a rollback that leaves the version string behind makes
the log say the wrong thing about every row it writes afterwards.
