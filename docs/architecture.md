# Engineering decisions

This page lists the decisions for which a reasonable alternative existed. The evaluation
protocol is described in [`protocol.md`](protocol.md), the data in
[`data-source.md`](data-source.md), and the operation of the service in
[`operations.md`](operations.md).

## Where the code lives

```
src/attrition_serving/
├── api/             routes, request and response models, settings, dependencies
├── data/            reading the extracts, the join, the anonymisation, the cleaning,
│                    the derived features, the mapping to the IBM dataset
├── db/              the engine, and the operations on the decision log
├── modeling/
│   ├── protocol.py  the evaluation protocol behind the published numbers
│   └── ...          estimators, grid search, single-split metrics
├── analysis/        exploration, univariate tests, SHAP
├── preprocessing.py the preprocessing steps; the artefact refers to this module path
└── utils/paths.py   the project's directories, resolved from one root
```

`modeling/protocol.py` holds the evaluation procedure: the repeated cross-validation, the
choice of threshold inside each fold, the recalibration arms, the cost curve, the reliability
bins and the subgroup table. `scripts/run_evaluation.py` sets the arm and the cost ratio that
ship. Before this module existed, these steps were spread over two notebooks, where choosing a
threshold on the test set looked like any other line of code.

The artefact depends on a module path. `models/pipeline.joblib` pickles a reference to
`_log1p_safe`, a function defined in `preprocessing.py`, so the file can be loaded only by a
package that still has that module at that path. Renaming the package once made the shipped
model unloadable, and no test detected it because no test opened the file.
`tests/unit/api/test_served_threshold.py` now loads the artefact and scores the ten fixtures.

## How the threshold is configured

`models/model_card.json` carries the threshold, and `api/settings.py` reads it.
`MODEL_THRESHOLD` lets an operator override it, and `.env.example` leaves that variable empty.
When neither the variable nor the card provides a threshold, `get_config` raises an error. The
configuration is loaded by the first request that needs it, so the process still starts and
`/health` still answers, and every route that requires the key then fails with a server error.

These measures exist because the service once read a key that the export does not write and
applied 0.5, a value that no analysis in the repository justified.
[`protocol.md`](protocol.md#the-six-things-that-were-wrong) gives the numbers.

## Paths and environment files

`utils/paths.py` finds the repository root by looking for `pyproject.toml`, and the other
directories are derived from it. No other module computes a root, and no code inserts into
`sys.path`. A second way of locating files would disagree with the first whenever a script
runs from another directory, and three places still locate files that way.
`scripts/db_apply_schema.py`, `scripts/db_run_checks.py` and `apply_schema` in
`db/serving_ops.py` open the SQL files under `sql/serving/` through a path relative to the
working directory, so they work only from the repository root.

`env.py` is the only module that loads a dotenv file. It honours `SKIP_DOTENV=1` and never
overwrites a variable that is already set. Before this, `api/settings.py` had its own loader,
which ignored the flag and loaded `.env.local` with `override=True`. On a machine where the
setup had created `.env.local`, the test of the served threshold had its environment
overwritten by that file despite setting `SKIP_DOTENV` itself, so it could pass or fail for the
wrong reason.

## File formats

The joined frame and the feature frame are stored as Parquet, which keeps the column types when
a frame is read back. `scripts/build_frames.py` writes them under `data/processed/`, and
notebooks 01 and 03 write the same two files. The published tables under `reports/` are CSV
files, which a reader can open in a browser or a spreadsheet.
The evaluation summary is a JSON file.

## The API

The request and response shapes are Pydantic models, and the generated OpenAPI page is built
from them. The request model declares `features` as a mapping from names to simple values, so
the page does not name the 32 required features, which the service compares with
`models/expected_features.json`. `normalize_payload` accepts the spellings an HR export may use for
gender (`"M"`, `"F"`, `"Homme"`, `"Femme"`) and overtime (`"Oui"`, `"Non"`, `"yes"`, `"no"`),
and converts them to the 0/1 integers the model was trained on. The conversion happens once,
when the request arrives.

FastAPI declares a dependency through `Depends()` placed in a default argument.
`pyproject.toml` lists `fastapi.Depends`, `fastapi.Query` and `fastapi.Header` as immutable
calls for Ruff's bugbear rule B008, which flags function calls in default arguments. The rule
set that `pyproject.toml` selects does not include the bugbear rules, so this setting currently
has no effect.

The engine is created on the first request and then cached, and the application disposes of
its connection pool at shutdown. The docstrings of `api/deps.py` and `api/main.py` explain both
choices.

## What the repository leaves out

Drift is not monitored, since the project is archived. [`operations.md`](operations.md) names
the signal that a monitor would follow.

Notebook 05 runs a small grid search, with three values of `C` for the logistic regression and
four combinations for the forest. With 1 470 rows and a fold-to-fold spread of 0.058 on average
precision, a wider search would compare candidates whose differences are of the order of that
spread. For that reason the repository has no wider search and no gradient boosting.
[`protocol.md`](protocol.md#which-model-and-why) shows the forest scoring below the linear
model with overlapping intervals.

A single shared API key keeps the demonstration closed. It is not an authorisation model and
does not identify callers, and the decision log has no column for the caller. A service
feeding a real HR process would need to record who requested each decision.

At this scale, the repository relies on a frozen artefact, a model card next to it, and a
version string stored with each logged decision. It has no feature store and no model registry.
MLflow tracks the exploratory runs in the notebooks, and the service does not use it. Putting
MLflow on the serving path would add a component that this project does not operate.

## The tests, by tier

```bash
uv run pytest -q                          # everything; the integration tier skips in 3s
docker compose up -d && uv run pytest -q  # everything, integration included
```

Warnings are errors. `pyproject.toml` sets `filterwarnings = ["error"]` and adds no `ignore`
filter, so a deprecation warning raised by a dependency fails the run.

The unit tier covers the protocol (a threshold chosen on a split that the scoring fold does
not contain, a costlier miss lowering the optimal threshold, equal-population reliability bins,
a subgroup with too few departures reporting its count without a rate). It also covers the
served threshold against the artefact, the payload normalisation, the alignment of request
columns with training columns, and the mapping in `data/source.py` against the profile the
extracts must match.

The integration tier sends predictions through `/predict`, checks that a prediction adds a row
to `predictions`, and reads predictions back through `/history`. It empties `predictions` before
each test. Without a database these tests skip, and the skip message gives the command that
starts one. A connect timeout of three seconds keeps the skip short. According to the docstrings
of the integration tier, these tests took four and a half minutes to finish on a machine without
a database before the timeout was set.

The system tier launches the service as a separate process, without a usable database, and sends
it a hundred payloads built from the ten fixtures over HTTP. It compares the share of payloads
flagged with the alert rate that `reports/cost_curve.csv` publishes at the shipped ratio, with a
tolerance of three standard deviations across the five repeats. It also checks that the key is
required, that an answer carries the model card's threshold, and that `stored` is false when
the log cannot be written. These checks run against a live process, and this is the only tier
that starts one.

Coverage is measured on every run, and `pyproject.toml` sets a floor of 54 %. The floor has
kept that value since it was introduced. The published coverage report gives a line rate of
56 % and a combined line-and-branch rate of 55 %, which is the figure the floor applies to.
