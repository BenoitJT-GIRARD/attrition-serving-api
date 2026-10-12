# Engineering decisions, and what was deliberately left out

What follows is the short list of decisions that had a defensible alternative. The evaluation
protocol is in [`protocol.md`](protocol.md), the data in
[`data-source.md`](data-source.md), and everything about running the service in
[`operations.md`](operations.md).

## Where the code lives

```
src/attrition_serving/
├── api/             routes, request and response models, settings, dependencies
├── data/            reading the extracts, the join, the anonymisation, the cleaning
├── db/              the engine, and the decision log's operations
├── modeling/
│   ├── protocol.py  the evaluation protocol; nothing publishes around it
│   └── ...          estimators, tuning, single-split metrics
├── analysis/        exploration, univariate tests, SHAP
├── preprocessing.py the fitted transformers -- the artefact names this path
└── utils/paths.py   where the project's files are; nothing else resolves a root
```

The split that matters is between `modeling/protocol.py` and the rest. It holds every decision
that turns data into a published number, and no other module is allowed to make one. Before,
those decisions were scattered across two notebooks, where choosing a threshold on the test set
looked like any other line of code.

The artefact names a module path: `models/pipeline.joblib` pickles transformers defined
in `preprocessing.py`, so the file is only loadable by a package that still has that module at
that path. Renaming the package once made the shipped model unloadable and nothing noticed,
because no test opened it; `tests/unit/` now does.

## The threshold lives in one place

`models/model_card.json` carries it, `api/settings.py` reads it, and the service refuses to
start when the card has no threshold. `MODEL_THRESHOLD` is an operator override and not the
source of the default, and `.env.example` deliberately leaves it empty.

Those are five locks on one invariant. They exist because this service once read a key the
export does not write and served 0.5 instead, a value nothing in the repository chose.
[`protocol.md`](protocol.md#the-six-things-that-were-wrong) has the numbers.

## One root, one environment loader

`utils/paths.py` finds the repository root by looking for `pyproject.toml`, and every other
path hangs off it. Nothing else computes a root, nothing inserts into `sys.path`, and no
artefact is read through a path relative to the working directory. Any of those would be a
second way of locating files, and the two ways would disagree as soon as someone ran a script
from another directory.

`env.py` is the only module that loads a dotenv file, and it honours `SKIP_DOTENV=1`. That
used to be false: `api/settings.py` had its own loader, which ignored the flag and loaded with
`override=True`. On the machine of anyone who had followed the setup and created `.env.local`,
the test that asserts the served threshold had its environment overwritten by that file,
despite setting `SKIP_DOTENV` itself, and could pass or fail for the wrong reason.

## Parquet between the steps, CSV for what is published

The join and the feature frame are written as Parquet: typed columns, and a frame that reads
back as it was written. Published tables are CSV so that a reader can open them: the files in
`reports/` are meant to be clicked on rather than loaded.

## The API surface

Request and response shapes are Pydantic models, so the generated OpenAPI page describes the
service as it is, where a hand-written page would drift.
`normalize_payload` accepts what an HR export contains (`"M"`, `"Oui"`, `"11 %"`)
and converts it once, at the edge, so the model never sees a string it has to guess about.

`Depends()` in a default argument is how FastAPI declares a dependency, and the linter's rule
against mutable defaults is switched off for those three callables only.

The engine is created at import and the pool is returned at shutdown. Both are written down
in `api/deps.py` and `api/main.py` next to the default they correct.

## What is not there, and why

Drift is not monitored, because this is an archived project. The signal that would be watched
is named in [`operations.md`](operations.md), and nothing watches it.

With 1 470 rows and a fold-to-fold spread of 0.058 on average precision, neither a
hyper-parameter search nor gradient boosting would give a readable result, so there is neither.
[`protocol.md`](protocol.md#which-model-and-why) shows the forest losing to the linear model
with overlapping intervals.

One shared API key keeps a demonstration closed, but it is not an authorisation model and gives
no per-caller identity: the decision log records *what* was decided and never *by whom*, a
question a service feeding a real HR process would have to answer.

A frozen artefact, a card beside it, and a version string logged with every decision are what
this scale needs, so there is no feature store and no model registry. MLflow tracks the
exploratory runs in the notebooks and nothing else; moving it onto the serving path would add a
component nobody here operates.

## The tests, by tier

```bash
uv run pytest -q                          # everything; the integration tier skips in 3s
docker compose up -d && uv run pytest -q  # everything, integration included
```

Warnings are errors. The suite has no blanket `ignore::`: a deprecation in a dependency fails
the run instead of scrolling past.

The unit tier covers the protocol (a threshold chosen on a split the scoring fold never sees, a
costlier miss lowering the optimal threshold, equal-population reliability bins, a subgroup with
too few events reporting its count and no rate); the served threshold against the artefact; the
payload normalisation; the train/serve column alignment; and the mapping in `data/source.py`
against the profile the extracts have to show.

The integration tier writes a prediction to PostgreSQL and has `/history` return it with the
threshold and the model version that produced it. Without a database these tests skip, and the
skip message is the command that would start one. The connect timeout is why skipping takes
three seconds instead of the four and a half minutes it once did.

The system tier starts the service in its own process, scores a hundred payloads built from the
ten fixtures through HTTP, and checks the observed alert rate against the fold interval the
protocol published. It answers "does the product do what the README says", which no unit test
can.

Coverage is measured on every run with a floor in `pyproject.toml`. The floor is a
ratchet: it goes up when the suite grows and never down.
