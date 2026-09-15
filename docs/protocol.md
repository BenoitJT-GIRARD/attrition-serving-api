# The evaluation protocol, and what it costs to publish a number

Every figure this repository publishes comes out of `src/attrition_serving/modeling/protocol.py`
and out of `scripts/run_evaluation.py`, which calls it. Nothing is quoted from a notebook.

This page says what the protocol does, what each published name means, and what the six
corrections it forced were worth in numbers.

## What a run does

`uv run python scripts/run_evaluation.py` — a few minutes, no GPU. It scores the 1 470 rows
under a 5×5 repeated stratified cross-validation: five folds, five different splitting seeds,
so every employee is scored five times by a model that never saw them in training. That is
7 350 scored rows and 1 185 departures across the 25 folds.

Inside each fold, in this order:

1. a quarter of the training part is held out as an **inner validation split**;
2. the model is fitted on the rest;
3. the recalibration, when the arm uses one, is fitted without the scoring fold;
4. the **threshold** is read off the inner validation split;
5. the scoring fold is scored once, with that threshold, and never looked at again.

The scoring fold takes part in no decision — not the threshold, not the recalibration, not
the subgroup cut points. That sentence is the whole protocol; the rest is bookkeeping.

## The three arms

The service returns a number called `proba_depart` and writes it to a database column of the
same name, so it has to be a probability. `class_weight="balanced"` makes the scores rank well
and lie, so three arms are run and compared.

<!-- source: ../reports/evaluation_summary.json -->
| arm | what it does | average precision | roc auc | calibration error | mean predicted risk | n |
|---|---|---|---|---|---|---|
| `none` | raw scores | **0.607 ± 0.058** | 0.823 ± 0.029 | 0.214 | 0.375 | 7350 |
| `holdout` | isotonic on the inner validation split | 0.551 ± 0.057 | 0.817 ± 0.030 | 0.020 | 0.164 | 7350 |
| `crossfit` — what ships | isotonic cross-fitted over the training fold | 0.569 ± 0.058 | 0.820 ± 0.028 | **0.015** | 0.163 | 7350 |

n = 7 350 scored rows, 1 185 departures, over 25 folds. `±` is the standard deviation between
folds. The base rate is 0.161.

Recalibration costs average precision, 0.607 down to 0.569. A comment in this repository once
claimed it could not, on the grounds that a monotone transform reorders nothing. That was
wrong: isotonic regression is a *step* function, it maps distinct scores onto one value, and
ties are exactly what average precision penalises. ROC AUC barely moves — 0.823 to 0.820 —
which is how one can see the ordering survived. Fitting the calibrator across the whole
training fold instead of one held-out split recovers a third of the loss, and that is why the
shipped arm is `crossfit` and not `holdout`.

## The threshold is a cost decision

A model ranks. It does not say where a retention conversation starts. That line depends on
what a departure costs compared to an hour spent on a conversation nobody needed, and the
protocol reports the whole curve instead of picking for the reader.

<!-- source: ../reports/cost_curve.csv -->
| a missed departure is worth… | threshold | alert rate | recall | precision |
|---|---|---|---|---|
| 1 conversation | 0.546 | 8 % | 36 % | 0.77 |
| 2 conversations | 0.366 | 13 % | 50 % | 0.62 |
| 3 conversations | 0.277 | 18 % | 59 % | 0.53 |
| 5 conversations | 0.162 | 26 % | 69 % | 0.44 |
| **8 conversations — shipped** | **0.111** | **37 %** | **78 %** | **0.35** |
| 13 conversations | 0.065 | 53 % | 87 % | 0.27 |
| 20 conversations | 0.052 | 64 % | 91 % | 0.24 |
| 30 conversations | 0.021 | 98 % | 100 % | 0.16 |
n = 7 350, so every share above is a share of 7 350 scored rows over 25 folds.
`reports/cost_curve.csv` carries the eight ratios with the fold-to-fold spread of each.

Eight is an assumption, not a measurement, and it is the one number here an employer would
replace with their own. Past a ratio of about 13 the list stops being a list: the service
flags one employee in two, and the last row of the table is a model that flags everybody and
has stopped deciding anything.

## What each published name means

`metrics.yaml` at the repository root carries the definitions the audit checks. In short:

- **Average precision** — the area under the precision-recall curve. On a problem with a
  16 % base rate, a model that learns nothing scores 0.161, so the number is read against
  that, not against zero.
- **ROC AUC** — how well the model orders employees, insensitive to where the threshold sits.
  It is here to separate *ordering* from *scale*, which is what the calibration rows turn on.
- **Calibration error** — the expected calibration error over equal-population bins: the gap
  between a predicted 0.3 and the share of that bin who actually left. Equal-population and
  not equal-width, because the scores pile up near zero.
- **Alert rate** — the share of employees the service flags at the shipped threshold.
- **Recall optimism** — the recall obtained on the inner validation split minus the recall
  obtained on the scoring fold. It is the price of choosing a threshold on the data that then
  measures it, and it is published because the previous version of this repository paid it
  without saying so.

## Who the alerts land on

The same model, at the shipped threshold, by attribute.

<!-- source: ../reports/subgroups.csv -->
| attribute | group | n | base rate | alert rate | recall |
|---|---|---|---|---|---|
| gender | female | 2 940 | 0.148 | 34 % | 77 % |
| gender | male | 4 410 | 0.170 | 39 % | 76 % |
| marital status | single | 2 350 | 0.255 | 50 % | **86 %** |
| marital status | divorced | 1 635 | 0.101 | 26 % | 78 % |
| marital status | married | 3 365 | 0.125 | 32 % | **63 %** |
| department | Sales | 2 230 | 0.206 | 45 % | 79 % |
| department | R&D | 4 805 | 0.138 | 32 % | 75 % |
| department | HR | 315 | 0.190 | 46 % | 82 % |

Each group is flagged at roughly twice its own departure rate — the ratio sits between 2.0 and
2.6 across all eight — so no group is over-flagged relative to how often it actually leaves.

The last column is not so even. The model finds 86 % of departures among single employees and
63 % among married ones. No correction is applied and no fairness claim is made. The HR group
holds 315 scored rows, which is 63 employees scored five times: its 82 % rests on about twelve
departures, and a difference of one employee moves it by eight points.

`reports/subgroups.csv` carries the same table, with the same labels: the translation from
the extracts' French happens in `protocol.py`, so the CSV a reader opens to check this page
says what this page says.

## Which model, and why

<!-- source: ../reports/baselines.csv -->
| model | average precision | roc auc | n |
|---|---|---|---|
| constant baseline | 0.161 ± 0.002 | 0.500 ± 0.000 | 7350 |
| **logistic regression** | **0.607 ± 0.058** | 0.823 ± 0.029 | 7350 |
| random forest | 0.531 ± 0.057 | 0.804 ± 0.038 | 7350 |

n = 7 350 scored rows over 25 folds, same protocol for all three.

The forest does not beat the linear model on 1 470 rows and 32 features, and its interval
overlaps. The linear model can be read coefficient by coefficient, which on a decision that
sends a manager to talk to a named person is a requirement.

No hyper-parameter search and no gradient boosting appear anywhere. With a fold-to-fold spread
of 0.058 on average precision, no comparison finer than that is readable on this dataset.

## The six things that were wrong

None of them were in what the code computed. All six were in what the repository *claimed*,
which is the kind of defect that survives a passing test suite.

**The service decided at a threshold nothing documented.** The settings module read
`model_card["threshold_default"]`; the export script writes `default_threshold`. The lookup
missed on every request and fell back to 0.5 — and `.env.example`, the file the documentation
tells you to copy, set 0.5 as well.

<!-- source: ../reports/evaluation_summary.json -->
On the n = 147 rows of the split that was published then, **24 of them leavers**, the
service at 0.5 found fifteen and missed nine; the threshold the model card declared would
have found twenty and missed four. A key name, and the deployed service found two thirds
of what its own documentation promised.
A missing threshold is now an error: `tests/unit/test_served_threshold_matches_artifact.py`
loads the artefact, calls the service, and fails when the two disagree.

**The threshold was chosen on the test set.** `find_threshold_for_recall(y_test, p_test,
target_recall=0.80)` — the recall of 0.80 was not a property of the model, it was the
definition of the threshold, measured on the same 147 rows that reported it. It is now chosen
inside each fold. The optimism that removes is +0.007 of recall on the shipped arm: the leak
was real, and its effect on the point estimate was not large. Saying so is worth more than
implying it was.

<!-- source: ../reports/evaluation_summary.json -->
**Everything rested on 24 events**, n = 147 test rows. The split was 90/10, 24 of them leavers.
Bootstrapped over 2 000 resamples, average precision on that set spans [0.355, 0.726] and
recall spans [0.667, 0.962]. "Recall = 0.80" was indistinguishable from 0.70 and from 0.95,
and the repository published four decimals on it.

Cross-validation over all 1 470 rows replaced it, and the comparison runs the opposite way
from what one would expect. The published split gave 0.546 average precision, **above only
16 % of the folds**. The repository was under-reporting its own model.

**Three files gave three different numbers**, and one of them was produced by no code in the
repository at all. It is deleted. `scripts/run_evaluation.py` writes every published table
now, and `models/model_card.json` cites it.

**The probability was not a probability.** In the bin where the model predicted 0.57, the
observed departure rate was 0.17. The three arms above are what replaced the single number.

**The API required five fields it never read.** The feature contract was built from every
column of the training frame, so a caller had to send the anonymised employee id and both join
keys to get a prediction — all three dropped before the model saw them. One of the five was
the previous pay rise, which the service carefully normalised on the way in. Parsed and added
back as a feature, average precision goes from 0.608 to 0.604 against a fold spread of 0.056:
it changes nothing, and the contract was the defect.

## What this does not prove

<!-- source: ../reports/evaluation_summary.json -->
**n = 1 470 rows at a base rate of 0.161 is a small dataset.** Cross-validation narrows the
intervals; it does not create information.

**The cost ratio is an assumption.** The shipped threshold is exactly as defensible as the
ratio of eight that produced it.

**Nothing here establishes cause.** A variable that separates leavers from stayers can be a
symptom of the decision to leave: someone who has decided to go stops asking for training. A
cross-section cannot tell the two apart. The model ranks risk; it names no lever to pull.

**The subgroup table describes, it does not guarantee.** It shows a recall gap between married
and single employees, establishes nothing about why, and corrects nothing.

**No drift monitoring.** A model served without it would have to be re-evaluated on new data
before being trusted a year from now. `docs/operations.md` says which signal would be watched.
