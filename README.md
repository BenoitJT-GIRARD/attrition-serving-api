---
title: Attrition serving — FastAPI + PostgreSQL + CI/CD
sdk: docker
app_port: 7860
---

# Attrition serving

A model that flags employees at risk of leaving, served behind an API that records every
decision it makes.

**Project status** — finished, and archived in a runnable state. The CI is frozen to manual
trigger so that nothing here decays into a red badge on a project nobody maintains.

## The problem

An HR team that wants to keep people has to know who is about to go, early enough to talk to
them. A model can rank employees by risk. What it cannot do is decide who gets a
conversation — that is a threshold, and the threshold is the entire product.

Set it high and the list is short and mostly right, and most of the people who leave are not
on it. Set it low and you catch nearly everyone, on a list so long that no HR team works
through it. Somewhere between the two is a number that depends on something the model does
not know: what a departure costs, compared to an hour spent on a retention conversation that
was never needed.

So this repository is built around two questions a model alone does not answer. **At what
threshold should it decide, and who can check that it decided there?**

The data is 1,470 employees from three internal extracts — contract and demographics, annual
reviews, an internal survey — joined on the employee. 237 of them left, a base rate of 16%.
That imbalance is why accuracy appears nowhere in this README: predicting "stays" for
everyone scores 84% and finds nobody.

## What it does

A FastAPI service loads a calibrated logistic regression and exposes five routes. `/predict`
scores a full feature payload, `/predict_by_id` scores an employee already in the database,
`/history` returns what was decided and when.

Every prediction writes a row to PostgreSQL: the probability, the threshold that turned it
into a decision, and the version of the model that produced it. That is the part worth
looking at. A probability on its own does not let anyone reconstruct, six months later, why a
particular person was flagged.

![A prediction, executed and written to PostgreSQL with its threshold and model version](docs/images/prediction-logged.png)

## The result

The model is scored by 5×5 repeated stratified cross-validation over all 1,470 rows — 25
folds, 7,350 scored rows, 1,185 departures — and every figure is published with the spread it
has across those folds.

| | Average precision | ROC AUC | Calibration error | Mean predicted risk |
|---|---|---|---|---|
| raw scores | **0.607 ± 0.058** | 0.823 ± 0.029 | 0.214 | 0.375 |
| **calibrated — what ships** | 0.569 ± 0.058 | 0.820 ± 0.028 | **0.015** | 0.163 |

Against a base rate of 0.161. Average precision is the metric that means something on an
imbalanced problem: a model that learns nothing scores 0.161 — the base rate itself — and
this one scores between three and four times that.

Those two rows are a trade, and choosing between them is the central decision here. Raw
scores rank slightly better; calibrated scores are the only ones whose value means what it
says. The service returns a number called `proba_depart` and writes it to a database column
of the same name, so it has to be a probability — and uncalibrated it was not, predicting an
average risk of 0.375 against a true rate of 0.161.

**The shipped operating point is a threshold of 0.110 on the calibrated scale.** It is the
expected-cost minimum when one missed departure is worth eight unnecessary retention
conversations. There, the service flags 37% of employees and catches 78% of the people who
leave.

Eight is an assumption, not a measurement, and it is the one number here an employer would
replace with their own. `reports/cost_curve.csv` publishes seven other ratios and what each
implies:

| A missed departure is worth… | Threshold | Employees flagged | Departures caught |
|---|---|---|---|
| 3 conversations | 0.277 | 18% | 59% |
| 5 conversations | 0.162 | 26% | 69% |
| **8 conversations** | **0.110** | **37%** | **78%** |
| 13 conversations | 0.065 | 53% | 87% |

Past a point the list stops being usable: at a ratio of 13 the service flags one employee in
two, and an HR team that gets an alert for half the company ignores the system. That is a
limit of the product, not of the model.

### Who the alerts land on

The same model, at the shipped threshold, by attribute:

| Attribute | Group | Actual departure rate | Flagged | Departures caught |
|---|---|---|---|---|
| gender | 0 | 0.148 | 34% | 77% |
| gender | 1 | 0.170 | 39% | 76% |
| marital status | single | 0.255 | 50% | **86%** |
| marital status | divorced | 0.101 | 26% | 78% |
| marital status | married | 0.125 | 32% | **63%** |
| department | Sales | 0.206 | 45% | 79% |
| department | Consulting | 0.138 | 32% | 74% |
| department | HR | 0.190 | 46% | 82% |

Every group is flagged at roughly twice its own departure rate — the ratio sits between 2.0
and 2.6 across all eight — so no group is over-flagged relative to how often it actually
leaves.

The last column is not so even. The model finds 86% of departures among single employees and
63% among married ones. A retention programme built on this would systematically miss more
people in one group than another. No correction is applied and no fairness claim is made; on
1,470 rows, publishing the table is the honest move.

### Which model, and why

| Model | Average precision | ROC AUC |
|---|---|---|
| constant baseline | 0.161 ± 0.002 | 0.500 |
| **logistic regression** | **0.607 ± 0.058** | 0.823 |
| random forest | 0.531 ± 0.057 | 0.804 |

The forest does not beat the linear model on 1,470 rows and 32 features. The linear model can
be read coefficient by coefficient, which on a decision that sends a manager to talk to a
named person is a requirement rather than a preference.

## Why these numbers can be believed

They are not the figures this repository published first. Six things were wrong, all six in
what it *claimed* rather than in what it computed. Each is given with the number before and
the number after, because a correction nobody can check is not one.

**The service decided at a threshold nothing documented.** The settings module read
`model_card["threshold_default"]`; the export script writes `default_threshold`. The lookup
missed on every request and fell back to 0.5 — and `.env.example`, the file the documentation
tells you to copy, set 0.5 as well. Both routes to the threshold led to a value nothing
justified, while every published figure said 0.32.

| Threshold | Precision | Departures caught | Missed |
|---|---|---|---|
| **0.500 — what the service used** | 0.319 | **63%** | **9 of 24** |
| 0.320 — what the model card said | 0.274 | 83% | 4 of 24 |

A key name, and the deployed service found two-thirds of what its own documentation promised.
A missing threshold is now an error rather than a default: serving an undocumented operating
point is worse than refusing to start. A test loads the artefact, calls the service, and fails
if the two disagree.

**The threshold was chosen on the test set.** `find_threshold_for_recall(y_test, p_test,
target_recall=0.80)` — the recall of 0.80 was not a property of the model, it was the
definition of the threshold, measured on the same 147 rows that reported it. It is now chosen
inside each fold, on a validation split the scoring fold never sees. The optimism that removes
is +0.007 of recall: the leak was real, its effect on the point estimate was not. Saying so is
worth more than implying it was large.

**Everything rested on 24 events.** The split was 90/10 — 147 test rows, 24 departures.
Bootstrapped over 2,000 resamples, average precision on that set spans [0.355, 0.726], and
recall spans [0.667, 0.962]. "Recall = 0.80" was indistinguishable from 0.70 and from 0.95,
and the repository published four decimal places on it.

Cross-validation over all 1,470 rows replaced it — and the comparison runs the opposite way
from what you would expect. The published split gave 0.546 average precision, **above only
16% of the folds**. The repository was under-reporting its own model.

**Three files gave three different numbers**, and one of them was produced by no code in the
repository at all. It is deleted. One script writes the figures now, and the model card cites
it.

**The probability was not a probability.** `class_weight="balanced"` makes the scores rank
well and lie: in the bin where the model predicted 0.57, the observed departure rate was 0.17.
Isotonic recalibration brings the calibration error from 0.214 to 0.015.

It costs average precision — 0.607 to 0.569 — and a comment in this code first claimed it
could not, on the grounds that a monotone transform cannot reorder anything. That was wrong,
and running a third arm is what caught it: isotonic is a *step* function, it maps distinct
scores onto one value, and ties are exactly what average precision penalises. ROC AUC moves
only from 0.823 to 0.820, which is how you can see the ordering survived. Fitting the
calibrator across the whole training fold rather than one held-out split recovers a third of
the loss.

**The API required five fields it never read.** The feature contract was built from every
column of the training frame, so a caller had to send the anonymised employee id and both join
keys to get a prediction — all three dropped before the model saw them. One of the five was
the previous pay rise, which the service carefully normalised on the way in. Worth checking
rather than assuming: parsed and added back as a feature, average precision goes from 0.608 to
0.604 against a fold spread of 0.056. It changes nothing. The contract was the defect.

## Running it

```bash
uv sync --group dev --group db --group serve
cp .env.example .env.local          # set API_KEY; leave MODEL_THRESHOLD unset
docker compose up -d                # PostgreSQL
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
```

Regenerate every published figure — a few minutes, no GPU:

```bash
uv run python scripts/data_quality_report.py   # the data dossier
uv run python scripts/run_evaluation.py        # 3 arms x 25 folds, cost curve, calibration
uv run python scripts/train_export_pipeline.py # the artefact and its card
```

Serve it:

```bash
uv run uvicorn attrition_serving.api.main:app --port 8000
```

![The API surface at /docs](docs/images/api-docs.png)

Every route except `/health` requires an `X-API-Key` header.

## Documentation

| Document | What it answers |
|---|---|
| [`docs/API.md`](docs/API.md) | Every route, the exact payload, and what each error code means |
| [`docs/DB.md`](docs/DB.md) | The schema, the decision log, and what each column records |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Local, container, hosted, and the CI in between |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | What to check, in what order, when the service answers badly |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Where the secrets are, what is anonymised, and what is not protected |
| [`docs/TESTING.md`](docs/TESTING.md) | What each family of tests guarantees |

## Structure

```
├── data/                          # HR records: not committed; ten request fixtures only
├── docs/                          # the six documents above
├── models/
│   ├── pipeline.joblib            # the shipped model, calibrated
│   ├── model_card.json            # threshold, cost ratio, CV metrics, scikit-learn version
│   └── expected_features.json     # the 32 features the model consumes
├── notebooks/                     # ingestion, EDA, features, baselines, tuning
├── reports/                       # every published figure
│   ├── evaluation_cv.csv          #   one row per fold per arm
│   ├── evaluation_summary.json    #   means, spreads, calibration, the old split compared
│   ├── baselines.csv              #   the three model families
│   ├── cost_curve.csv             #   the threshold each cost ratio implies
│   ├── calibration.csv            #   reliability, equal-population bins, per arm
│   ├── subgroups.csv              #   flag rate and recall per group
│   └── data_quality.csv, cleaning_trace.csv, redundant_features.csv, feature_encoding.csv
├── scripts/                       # data quality, evaluation, export, database
├── sql/                           # exploratory views, and the serving schema
├── src/attrition_serving/
│   ├── api/                       # routes, settings, dependencies
│   ├── protocol.py                # the evaluation protocol; nothing publishes around it
│   └── ...                        # cleaning, features, modelling, database
└── tests/                         # unit and integration; the integration ones skip in 3s
```

## What this does not prove

**1,470 rows and 237 departures is a small dataset.** Cross-validation narrows the intervals;
it does not create information. Average precision is 0.607 with a fold-to-fold spread of
0.058, and no comparison finer than that is readable here — which is why no hyper-parameter
search and no gradient boosting appear.

**The cost ratio is an assumption.** Eight conversations per missed departure is a number
chosen to make the threshold explicit, not one an employer supplied. The shipped threshold is
exactly as defensible as that ratio.

**Nothing here establishes cause.** A variable that separates leavers from stayers may be a
symptom of the decision to leave rather than a reason for it — someone who has decided to go
stops asking for training. A cross-section cannot tell the two apart. The model ranks risk; it
does not name levers to pull.

**The subgroup table describes, it does not guarantee.** It shows a recall gap between married
and single employees. It does not establish why, and nothing here corrects it.

**No drift monitoring.** A model served without it should be re-evaluated on new data before
being trusted a year from now.

## Licence and data

MIT, for the code.

The HR extracts are **not** in this repository. They are records about real employees, and a
repository is a public place. `data/` holds ten rows kept as request fixtures for the API
tests, and employee identifiers are anonymised with HMAC-SHA256 under a key that lives in the
environment. Every figure above reproduces from the scripts once the extracts are placed in
`data/raw/`.
