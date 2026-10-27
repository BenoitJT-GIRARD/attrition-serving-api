# The evaluation protocol

`src/attrition_serving/modeling/protocol.py` implements the evaluation, and
`scripts/run_evaluation.py` calls it and writes the tables and the summary under `reports/`
that this page quotes. The last section, about the earlier version of the repository, also
quotes figures from that version. Some of them come from the git history or from comments in
the code and cannot be recomputed by the current scripts, and the section says which.

This page describes what the protocol does, defines each published metric, and gives the
measured effect of the six corrections it led to.

## What a run does

`uv run python scripts/run_evaluation.py` needs no GPU. `reports/run-evidence.json` records
about 100 seconds for the whole chain of scripts that includes it. The script runs stratified
five-fold cross-validation, repeated five times with different shuffles, over the whole table.
Each of the 1 470 employees is therefore scored five times per arm, each time by a model that
did not see that employee during fitting. The totals are 7 350 scored rows and 1 185
departures.

Inside each fold, in this order:

1. a quarter of the training part is held out as an inner validation split;
2. the model is fitted on the remaining three quarters, and in the `crossfit` arm this model
   includes an isotonic recalibration cross-fitted over those rows;
3. in the `holdout` arm, an isotonic recalibration is fitted on the inner validation split;
4. the threshold is set to the highest value that still gives a recall of at least 0.80 on the
   inner validation split;
5. the model is refitted on the whole training part, the `crossfit` arm refitting its
   recalibration with it and the `holdout` arm reusing the one from step 3;
6. the scoring fold is scored once, at that threshold.

In these steps, the threshold and the recalibration are set before the scoring fold is read.
The cost curve, in the section on the threshold, chooses its thresholds by another method.

## The three arms

`class_weight="balanced"` gives the logistic regression a good ranking and inflates its scores
towards the positive class. The service returns the score under a name that promises a
probability, so the protocol runs three arms and measures what each one gains and loses.

<!-- source: ../reports/evaluation_summary.json -->
| arm | what it does | average precision | roc auc | calibration error | mean predicted risk | n |
|---|---|---|---|---|---|---|
| `none` | raw scores | **0.607 ± 0.058** | 0.823 ± 0.029 | 0.214 | 0.375 | 7350 |
| `holdout` | isotonic on the inner validation split | 0.551 ± 0.057 | 0.817 ± 0.030 | 0.020 | 0.164 | 7350 |
| `crossfit` (shipped) | isotonic cross-fitted over the training fold | 0.569 ± 0.058 | 0.820 ± 0.028 | **0.015** | 0.163 | 7350 |

n = 7 350 scored rows, 1 185 departures, over 25 folds. `±` is the standard deviation between
folds. The base rate is 0.161.

Recalibration costs 0.039 of average precision between the first row and the third, computed
before rounding. A comment in this repository once argued that this loss was impossible, because
a monotone map preserves order. Isotonic regression is a step function, however. It maps
distinct scores onto shared values, and average precision is penalised by the ties this creates.
ROC AUC changes by only 0.003, so the order of the employees is almost unchanged. In the
`crossfit` arm, the recalibration is fitted across the whole training part, whereas the
`holdout` arm fits it on a quarter of that part. Cross-fitting recovers about a third of the
loss that the `holdout` arm shows, and `crossfit` is the arm the service ships.

## How the threshold is chosen

Where the alert list should stop depends on the relative cost of losing an employee and of an
hour of a manager's time spent with someone who was going to stay. The model has no
information about that ratio, so the protocol computes the threshold for a range of ratios.

For each ratio and each of the five repeats, `cost_curve` in `protocol.py` takes the
out-of-fold scores of the shipped arm and finds the threshold that minimises expected cost. The
table gives the mean over the five repeats. Each threshold is chosen on the same scores that
its recall, precision and alert rate are computed from. The shipped threshold, 0.1105 in the
model card, is the mean of the five optima at a ratio of 8.

<!-- source: ../reports/cost_curve.csv -->
| a missed departure is worth… | threshold | alert rate | recall | precision |
|---|---|---|---|---|
| 1 conversation | 0.546 | 8 % | 36 % | 0.77 |
| 2 conversations | 0.366 | 13 % | 50 % | 0.62 |
| 3 conversations | 0.277 | 18 % | 59 % | 0.53 |
| 5 conversations | 0.162 | 26 % | 69 % | 0.44 |
| **8 conversations (shipped)** | **0.111** | **37 %** | **78 %** | **0.35** |
| 13 conversations | 0.065 | 53 % | 87 % | 0.27 |
| 20 conversations | 0.052 | 64 % | 91 % | 0.24 |
| 30 conversations | 0.021 | 98 % | 100 % | 0.16 |
> n = 7 350 scored rows, 1 470 in each repeat. The alert rate is a share of 1 470 rows,
> recall a share of the 237 departures in a repeat, and each share is averaged over the five
> repeats. `reports/cost_curve.csv` also gives the standard deviation of
> each column across the repeats.

> **How to read it.** Each row answers the question in the first column, and the rest of the
> row gives the consequences of that answer. The threshold is the score at or above which the
> service flags an employee. The alert rate is the share of all employees on the list. Recall
> is the share of the people who left that the list contains, and precision is the share of the
> list who really left. Reading downwards, the list gets longer, recall rises and precision
> falls.

The ratio is for the reader to set. From a ratio of 13 the list covers about half of the
employees, and at a ratio of 30 it covers 98 % of them. A list that long is of little use to
a retention programme.

## Definitions of the published metrics

`metrics.yaml` at the repository root defines each metric. In short:

- Average precision is the area under the precision-recall curve. With a 16 % base rate, a model
  that learns nothing scores 0.161, and the value is read against that baseline.
- ROC AUC measures how well the model orders employees, independently of any threshold. It is
  reported to separate the ordering of the scores from their scale, which is where the
  calibration arms differ.
- Calibration error is the expected calibration error over ten bins of roughly equal population.
  It is the average gap, weighted by bin size, between the mean predicted probability in a bin
  and the share of that bin who actually left. The bins are cut by population because the
  recalibrated scores are concentrated near zero, and with equal-width bins most of those
  predictions would fall into the first bin.
- Alert rate is the proportion of employees flagged at a given threshold.
- Recall optimism is the recall measured on the inner validation split, where the threshold was
  chosen, minus the recall measured on the scoring fold. It shows how much a recall measured on
  the data that chose the threshold overstates the recall on new data. The earlier version of
  the repository published such a recall without saying so.

## Alerts by subgroup

The out-of-fold scores of the shipped arm, at the shipped threshold, by attribute.

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

> **How to read it.** One row per group. R&D (research and development) and HR (human
> resources) are departments. The base rate is the observed share of the group who left. The
> alert rate is the share of the group the service puts on the list, and recall is the share of
> the group's own departures the list catches. A group alerted at about twice its base rate is
> treated like the others, and the groups differ mainly in the recall column.

The ratio of alert rate to base rate lies between 1.97 and 2.60 in all eight rows, so the
alert list tracks where departures occur.

Recall differs more between groups. The two extreme marital statuses differ by twenty-three
points, so a retention programme based on this list would reach a larger share of the single
employees who leave than of the married ones. The HR row rests on twelve leavers among 63
employees, each scored five times (60 departures in 315 scored rows). One employee moves its
recall by about eight points, so this row is better read as a count than as a rate.

`reports/subgroups.csv` carries the same table with the same labels. `protocol.py` translates
the French labels of the extracts, so the CSV and this page use the same words.

## Which model, and why

<!-- source: ../reports/baselines.csv -->
| model | average precision | roc auc | n |
|---|---|---|---|
| constant baseline | 0.161 ± 0.002 | 0.500 ± 0.000 | 7350 |
| **logistic regression** | **0.607 ± 0.058** | 0.823 ± 0.029 | 7350 |
| random forest | 0.531 ± 0.057 | 0.804 ± 0.038 | 7350 |

n = 7 350 scored rows over 25 folds, with the same protocol for all three models and no
recalibration.

The forest scores 0.077 below the logistic regression in average precision, computed before
rounding, and the fold-to-fold intervals of the two models overlap. On a dataset of this size,
the comparison does not separate the two model families. The linear model is kept because a
manager sent to talk to a named employee can be shown the coefficients that produced the alert.

## The six things that were wrong

The earlier version of the repository had six defects. Each is described below, with its
measured effect where one was measured.

**The service applied a threshold that no analysis justified.** The settings module read
`model_card["threshold_default"]`, and the export script wrote `default_threshold`. The lookup
always failed, so the service applied 0.5 to every decision. `.env.example`, the file the
documentation said to copy, also set 0.5, as did the CI workflow and the example response in
the API documentation of the time.

<!-- source: ../reports/evaluation_summary.json -->
The test split published at the time had n = 147 rows, **24 of them leavers**. At 0.5, the
service found fifteen of them and missed nine. The threshold the model card declared, 0.32,
would have found twenty and missed four. One key name therefore cost five of the twenty
departures that the model card's threshold would have found. These counts come from the
comment in `api/settings.py` and the docstring of the served-threshold test, which give the
corresponding recalls, 0.625 and 0.833. The current scripts do not recompute them.

A missing threshold is now an error. `tests/unit/api/test_served_threshold.py` builds the
service configuration with no override and fails when its threshold differs from the model
card's, and the system tier checks the same agreement against a running service.

**The threshold was chosen on a test set.** The tuning notebook ran
`find_threshold_for_recall(y_test, p_test, target_recall=0.80)` on its own 20 % test split, 294
rows with 47 leavers. The threshold was set to give a recall of 0.80 on the rows that then
reported that recall, so the reported recall held by construction. In the evaluation, the
threshold of each fold is now chosen on the inner validation split, and the shipped threshold
comes from the cost curve, as described in the section on the threshold. Measured as recall
optimism, the bias this removes is +0.007 of recall on the raw scores and +0.060 on the
recalibrated scores of the shipped arm, about six points of recall.

<!-- source: ../reports/evaluation_summary.json -->
**The published metrics rested on 24 departures**, out of n = 147 test rows in a 90/10 split.
Bootstrapped over 2 000 resamples, average precision on that split spans [0.355, 0.726] and
recall spans [0.667, 0.962]. No committed script computes this bootstrap. With such an
interval, a recall of 0.80 could not be told apart from 0.70 or from 0.95. The model card of
the time nevertheless gave the average precision of that split as 0.5460021752541807.

<!-- source: ../reports/evaluation_summary.json -->
Twenty-five folds over all n = 1 470 rows replaced that split, and the correction raised the
figure. Only **16 %** of the folds of the raw arm, 4 of 25, score below the old split's 0.546, so the
repository had been quoting a split near the low end of the distribution.

**Three result files disagreed.** The model card and `reports/api_model_metrics.json` gave a
threshold of 0.32 and an average precision of 0.546. `reports/final_metrics.json` gave 0.3426
and 0.5536. A notebook cell had once written that file, and it had since been removed, so no
code in the repository produced it any more. The file has been deleted. These four values come
from the files as they stand in the git history, for example
`git show f23c6ca^:reports/final_metrics.json`. The current scripts recompute only 0.546, as
the single-split average precision in `reports/evaluation_summary.json`.
`scripts/run_evaluation.py` now writes every evaluation table, and `models/model_card.json`
takes its threshold and metrics from that script's summary.

**The returned probability was miscalibrated.** In the bin where the raw model predicted 0.57,
the observed departure rate was 0.17. The three arms above replaced the single raw score, and
the service now returns the recalibrated probability of the `crossfit` arm.

**The API required five fields it never read.** The feature contract was built from every
column of the training frame. A caller therefore had to supply five columns the model never
consumed: the anonymised identifier `employee_id_anon`, the join keys `eval_number`,
`eval_number_int` and `code_sondage`, and the previous pay rise
`augementation_salaire_precedente`. The preprocessing lists the pay rise with another spelling,
`augmentation_salaire_precedente`, so the model never received it, although the service
normalised it on the way in. Parsed and added back as a feature, the pay rise moves average
precision from 0.608 to 0.604, against a fold spread of 0.056, so the field adds no measurable
value and the defect lay in the contract. No committed script runs that comparison.

## What this does not prove

The README lists, under the same heading, five limits that this protocol cannot remove. Four
of them come from the data and the design of the study, and the fifth, the absence of drift
monitoring, comes from the way the service is operated. The README states them next to the
numbers.
