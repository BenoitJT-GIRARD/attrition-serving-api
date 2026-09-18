# The evaluation protocol, and what it costs to publish a number

Every figure this repository publishes comes out of `src/attrition_serving/modeling/protocol.py`
and out of `scripts/run_evaluation.py`, which calls it. Nothing is quoted from a notebook.

This page says what the protocol does, what each published name means, and what the six
corrections it forced were worth in numbers.

## What a run does

`uv run python scripts/run_evaluation.py` — a few minutes, no GPU. Stratified five-fold
cross-validation, repeated under five splitting seeds, over the whole table: each of the 1 470
employees is therefore scored five separate times, always by a model fitted without them. The
totals are 7 350 scored rows and 1 185 departures.

Inside each fold, in this order:

1. a quarter of the training part is held out as an **inner validation split**;
2. the model is fitted on the rest;
3. the recalibration, when the arm uses one, is fitted without the scoring fold;
4. the **threshold** is read off the inner validation split;
5. the scoring fold is scored once, with that threshold, and never looked at again.

No decision is taken with the scoring fold in view: the threshold, the recalibration and the
subgroup boundaries are all settled before it is opened. Everything else in this module is
bookkeeping around that one rule.

## The three arms

`class_weight="balanced"` buys a good ranking and pays for it with the scale: the scores come
out inflated towards the positive class. Since the service publishes them under a name that
promises a probability, three arms are run and the trade between them is measured.

<!-- source: ../reports/evaluation_summary.json -->
| arm | what it does | average precision | roc auc | calibration error | mean predicted risk | n |
|---|---|---|---|---|---|---|
| `none` | raw scores | **0.607 ± 0.058** | 0.823 ± 0.029 | 0.214 | 0.375 | 7350 |
| `holdout` | isotonic on the inner validation split | 0.551 ± 0.057 | 0.817 ± 0.030 | 0.020 | 0.164 | 7350 |
| `crossfit` — what ships | isotonic cross-fitted over the training fold | 0.569 ± 0.058 | 0.820 ± 0.028 | **0.015** | 0.163 | 7350 |

n = 7 350 scored rows, 1 185 departures, over 25 folds. `±` is the standard deviation between
folds. The base rate is 0.161.

The 0.038 of average precision lost between the first row and the third is real, and a comment
in this repository once argued it was impossible because a monotone map preserves order. The
argument fails on one word: isotonic regression is a *step*, so distinct scores collapse onto a
shared value, and average precision charges for every tie thus created. ROC AUC moves by 0.003,
which is the signature of an ordering left intact. Cross-fitting the calibrator over the whole
training fold rather than one quarter of it returns about a third of the loss, and the shipped
arm is the one that does.

## The threshold is a cost decision

Ranking is one thing and deciding is another. Where the alert list stops depends on a price the
model has no access to: what losing somebody costs, against an hour of a manager's time spent on
somebody who was staying anyway. The protocol prices the whole range.

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

> **How to read it.** Each row is one answer to the question in the first column, and the rest
> of the row is what that answer costs. The threshold is the score at or above which the service
> flags somebody. The alert rate is the share of all employees who end up on the list. Recall is
> the share of the people who left that the list contains, and precision is the share of the
> list who really left. Reading downwards, a longer list always trades precision for recall.

The ratio is the reader's to set. Past about 13 the alert list covers one employee in two, and
the last row is a model that flags everybody: the curve has left the range where a retention
programme can act on it.

## What each published name means

`metrics.yaml` at the repository root carries the definition of each one. In short:

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

> **How to read it.** One row per group, where R&D (research and development) and HR (human
> resources) are departments. The base rate is the share of that group who actually left,
> measured and not predicted. The alert rate is the share of the group the service puts on the
> list, and recall is the share of the group's own departures the list catches. A group alerted
> on at roughly twice its base rate is being handled like every other; the recall column is
> where the groups genuinely separate.

The ratio of alert rate to base rate stays between 2.0 and 2.6 across the eight rows, so the
list tracks where departures actually happen.

Recall does not. Twenty-three points separate the two extreme marital statuses, which on a
retention programme means one group is served better than another for reasons the model was
never asked about. The HR row rests on about twelve events out of 315 scored rows: one employee
moves it by eight points, and it should be read as a count rather than as a rate.

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

The forest loses by 0.076 of average precision with overlapping intervals, so the comparison
settles nothing about the families and everything about the size of the dataset. The linear
model is kept for a reason the score does not carry: a manager sent to talk to a named person
can be shown the coefficients that produced the alert.

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

<!-- source: ../reports/evaluation_summary.json -->
Twenty-five folds over the full n = 1 470 rows replaced it, and the correction went the
direction nobody expects: the old split's 0.546 sits **below 0.84 of the folds**. The
repository had been quoting one of its unluckiest draws.

**Three files gave three different numbers**, and one of them was produced by no code in the
repository at all. It is deleted. `scripts/run_evaluation.py` writes every published table
now, and `models/model_card.json` cites it.

**The probability was not a probability.** In the bin where the model predicted 0.57, the
observed departure rate was 0.17. The three arms above are what replaced the single number.

**The API required five fields it never read.** The feature contract was built from every
column of the training frame. A caller therefore had to supply the anonymised identifier and
the two join keys, none of which reach the model. One of the five was
the previous pay rise, which the service carefully normalised on the way in. Parsed and added
back as a feature, average precision goes from 0.608 to 0.604 against a fold spread of 0.056:
it changes nothing, and the contract was the defect.

## What this does not prove

The five limits this protocol cannot lift are in the README, under that heading. They are limits
of the data and of the design, not of the measurement, which is why they are stated where a
reader meets the numbers rather than here.
