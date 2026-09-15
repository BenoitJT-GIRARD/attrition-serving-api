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

The split that matters is `modeling/protocol.py` against the rest. It holds every decision
that turns data into a published number, and it is the only module allowed to make one. The
previous arrangement scattered those decisions across two notebooks, where choosing a
threshold on the test set read like any other line of code.

**The artefact names a module path.** `models/pipeline.joblib` pickles transformers defined
in `preprocessing.py`, so the file is only loadable by a package that still has that module at
that path. Renaming the package once made the shipped model unloadable and nothing noticed,
because no test opened it; `tests/unit/` now does.

## The threshold lives in one place

`models/model_card.json` carries it, `api/settings.py` reads it, and the service **refuses to
start** when the card has no threshold. `MODEL_THRESHOLD` is an operator override and not the
source of the default, and `.env.example` deliberately leaves it empty.

That is five locks on one invariant, and they exist because this service once read a key the
export does not write. What it served instead was 0.5, which nothing in the repository chose.
[`protocol.md`](protocol.md#the-six-things-that-were-wrong) has the numbers.

## One root, one environment loader

`utils/paths.py` finds the repository root by looking for `pyproject.toml`, and every other
path hangs off it. Nothing else computes a root, nothing inserts into `sys.path`, and no
artefact is read through a path relative to the working directory: each of those is a second
answer to a question that already has one, and they disagree the day someone runs a script
from another directory.

`env.py` is the only module that loads a dotenv file, and it honours `SKIP_DOTENV=1`. That
used to be false: `api/settings.py` had its own loader, which ignored the flag and loaded with
`override=True`. On the machine of anyone who had followed the setup and created `.env.local`,
the test that asserts the served threshold had its environment overwritten by that file,
despite setting `SKIP_DOTENV` itself, and could pass or fail for the wrong reason.

## Parquet between the steps, CSV for what is published

The join and the feature frame are written as Parquet: typed columns, and a frame that reads
back as it was written. Published tables are CSV, because a number a reader cannot open is not
a published number — `reports/` is meant to be clicked on, not loaded.

## The API surface

Request and response shapes are Pydantic models, which is what makes the generated OpenAPI
page an accurate description of the service rather than a hand-written one that drifts.
`normalize_payload` accepts what an HR export actually contains (`"M"`, `"Oui"`, `"11 %"`)
and converts it once, at the edge, so the model never sees a string it has to guess about.

`Depends()` in a default argument is how FastAPI declares a dependency, and the linter's rule
against mutable defaults is switched off for exactly those three callables and no others.

The engine is created at import and the pool is returned at shutdown. Both are written down
in `api/deps.py` and `api/main.py` next to the default they correct.

## What is not there, and why

**No drift monitoring.** This is an archived project. The signal that would be watched is
named in [`operations.md`](operations.md), and nothing watches it.

**No hyper-parameter search, no gradient boosting.** With 1 470 rows and a fold-to-fold spread
of 0.058 on average precision, neither is readable. [`protocol.md`](protocol.md#which-model-and-why)
shows the forest losing to the linear model with overlapping intervals.

**No per-caller identity.** One shared API key is a lock on a demonstration, not an
authorisation model. It means the decision log records *what* was decided and never *by whom*,
which a service feeding a real HR process would have to answer.

**No feature store, no model registry.** A frozen artefact, a card beside it, and a version
string logged with every decision are what this scale needs. MLflow tracks the exploratory
runs in the notebooks and nothing else: promoting it to the serving path would be a component
nobody here operates.

## The tests, by tier

```bash
uv run pytest -q                          # everything; the integration tier skips in 3s
docker compose up -d && uv run pytest -q  # everything, integration included
```

Warnings are errors. The suite has no blanket `ignore::`: a deprecation in a dependency fails
the run instead of scrolling past.

**Unit** — the protocol (a threshold chosen on a split the scoring fold never sees, a costlier
miss lowering the optimal threshold, equal-population reliability bins, a subgroup with too few
events reporting its count and no rate); the served threshold against the artefact; the
payload normalisation; the train/serve column alignment; the mapping in `data/source.py`
against the profile the extracts have to show.

**Integration** — a prediction written to PostgreSQL, and `/history` returning it with the
threshold and the model version that produced it. Without a database they skip, and the skip
message is the command that would start one. The connect timeout is why that takes three
seconds instead of the four and a half minutes it once did.

**System** — the service started in its own process, a hundred fixtures scored through HTTP,
and the observed alert rate checked against the fold interval the protocol published. It is
the tier that answers "does the product do what the README says", which no unit test can.

Coverage is measured on every run with a floor in `pyproject.toml`. The floor is a ratchet,
not a target: it goes up when the suite grows and never down.
