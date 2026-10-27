# Where the data comes from

The three files under `data/raw/` are one public dataset cut into three parts. The dataset is
IBM's *HR Analytics Employee Attrition & Performance*, a sample dataset that IBM's data
scientists generated and published. The rows are fictional and describe no real person.

The data therefore needs no protection from a reader. The upstream file is public and the
correspondence below covers every column, so someone who has never seen the extracts can
rebuild them and recompute the published tables.

## Identifying the dataset

| | |
|---|---|
| Rows | 1 470, one per employee |
| Departures | 237, a base rate of 0.1612 |
| Columns the extracts carry | 34, covering 32 of IBM's 35 (`EmployeeNumber` appears in all three) |
| Columns IBM ships and the extracts drop | `DailyRate`, `HourlyRate`, `MonthlyRate` |
| Constant columns kept | `nombre_heures_travailless` = 80, `ayant_enfants` = `Y`, `nombre_employee_sous_responsabilite` = 1 |

These three constant columns match IBM's file, which has `StandardHours` = 80, `Over18` = `Y`
and `EmployeeCount` = 1 in all of its 1 470 rows.

`uv run python scripts/build_extracts.py --check` compares the files in `data/raw/` with the
signature of the dataset: the row count, the column names, and every range and value count of
the profile in `source.py`. It lists the disagreements it finds, at most twelve of them, and a
file whose column names differ is reported as a whole. Run it before quoting a number.

## Why the columns are in French

The extracts are a repackaging of the dataset. The columns were renamed in French and the
categories re-themed as a consulting firm: `Research & Development` became `Consulting`,
`Life Sciences` became `Infra & Cloud`, and `Sales Executive` became `Cadre Commercial`. No row
was resampled or perturbed, and the value counts match IBM's exactly.

Two French names suggest a content that the column does not hold.
`nombre_employee_sous_responsabilite` reads as "employees managed" and is `EmployeeCount`, a
constant 1. `nombre_heures_travailless` reads as "hours worked" and is `StandardHours`, a
constant 80. The feature engineering drops `nombre_heures_travailless`.
`nombre_employee_sous_responsabilite` stays among the 32 features that the model and the API
expect, and since it never varies, its permutation importance is zero.

## The correspondence, column by column

The correspondence was established by matching each column's range and, for categorical
columns, its exact value counts. `src/attrition_serving/data/source.py` holds the same table in
code, and the unit tests check it.

### `extrait_sirh.csv`: contract and demographics

| Extract | IBM | Values |
|---|---|---|
| `id_employee` | `EmployeeNumber` | 1 to 2 068, 1 470 distinct |
| `age` | `Age` | 18 to 60 |
| `genre` | `Gender` | `F` ← Female (588), `M` ← Male (882) |
| `revenu_mensuel` | `MonthlyIncome` | 1 009 to 19 999 |
| `statut_marital` | `MaritalStatus` | Célibataire ← Single (470), Marié(e) ← Married (673), Divorcé(e) ← Divorced (327) |
| `departement` | `Department` | Commercial ← Sales (446), Consulting ← Research & Development (961), Ressources Humaines ← Human Resources (63) |
| `poste` | `JobRole` | nine roles, renamed; counts in `source.py` |
| `nombre_experiences_precedentes` | `NumCompaniesWorked` | 0 to 9 |
| `nombre_heures_travailless` | `StandardHours` | constant 80 |
| `annee_experience_totale` | `TotalWorkingYears` | 0 to 40 |
| `annees_dans_l_entreprise` | `YearsAtCompany` | 0 to 40 |
| `annees_dans_le_poste_actuel` | `YearsInCurrentRole` | 0 to 18 |

### `extrait_eval.csv`: the annual review

| Extract | IBM | Values |
|---|---|---|
| `satisfaction_employee_environnement` | `EnvironmentSatisfaction` | 1 to 4, counts 284 / 287 / 453 / 446 |
| `note_evaluation_precedente` | `JobInvolvement` | 1 to 4, counts 83 / 375 / 868 / 144 |
| `niveau_hierarchique_poste` | `JobLevel` | 1 to 5, counts 543 / 534 / 218 / 106 / 69 |
| `satisfaction_employee_nature_travail` | `JobSatisfaction` | 1 to 4, counts 289 / 280 / 442 / 459 |
| `satisfaction_employee_equipe` | `RelationshipSatisfaction` | 1 to 4, counts 276 / 303 / 459 / 432 |
| `satisfaction_employee_equilibre_pro_perso` | `WorkLifeBalance` | 1 to 4, counts 80 / 344 / 893 / 153 |
| `eval_number` | `EmployeeNumber` | rendered `E_<number>` |
| `note_evaluation_actuelle` | `PerformanceRating` | 3 (1 244) or 4 (226) |
| `heure_supplementaires` | `OverTime` | Oui ← Yes (416), Non ← No (1 054) |
| `augementation_salaire_precedente` | `PercentSalaryHike` | rendered `"11 %"` … `"25 %"` |

The five columns scored from 1 to 4 can be told apart only by their distributions, since they
share the same range. `JobInvolvement` and `WorkLifeBalance` are concentrated on the value 3
(868 and 893 of the 1 470 rows), and the three satisfaction scales are spread more evenly.

### `extrait_sondage.csv`: the internal survey

| Extract | IBM | Values |
|---|---|---|
| `a_quitte_l_entreprise` | `Attrition` | Oui ← Yes (237), Non ← No (1 233) |
| `nombre_participation_pee` | `StockOptionLevel` | 0 to 3, counts 631 / 596 / 158 / 85 |
| `nb_formations_suivies` | `TrainingTimesLastYear` | 0 to 6, counts 54 / 71 / 547 / 491 / 123 / 119 / 65 |
| `nombre_employee_sous_responsabilite` | `EmployeeCount` | constant 1 |
| `code_sondage` | `EmployeeNumber` | zero-padded to six digits |
| `distance_domicile_travail` | `DistanceFromHome` | 1 to 29 |
| `niveau_education` | `Education` | 1 to 5, counts 170 / 282 / 572 / 398 / 48 |
| `domaine_etude` | `EducationField` | six fields, re-themed; counts in `source.py` |
| `ayant_enfants` | `Over18` | constant `Y` |
| `frequence_deplacement` | `BusinessTravel` | Aucun ← Non-Travel (150), Occasionnel ← Travel_Rarely (1 043), Frequent ← Travel_Frequently (277) |
| `annees_depuis_la_derniere_promotion` | `YearsSinceLastPromotion` | 0 to 15 |
| `annes_sous_responsable_actuel` | `YearsWithCurrManager` | 0 to 17 |

## Rebuilding the extracts

The extracts are not committed, because the repository has no licence covering the
redistribution of this repackaging of IBM's file. The upstream file is publicly available, so
the repository ships the procedure that rebuilds the extracts from it.

```bash
# 1. get WA_Fn-UseC_-HR-Employee-Attrition.csv — IBM sample data, mirrored on Kaggle
# 2. cut it into the three extracts, using the correspondence above
uv run python scripts/build_extracts.py --source path/to/WA_Fn-UseC_-HR-Employee-Attrition.csv
uv run python scripts/build_extracts.py --check
```

The script stops on any categorical value that the mapping does not name, and it runs the
signature check on the files it has written. `uv run python scripts/build_frames.py` then
builds the joined frame and the feature frame under `data/processed/`, with the same library
calls as notebooks 01 and 03. From those frames, `scripts/data_quality_report.py`,
`scripts/run_evaluation.py` and `scripts/train_export_pipeline.py` recompute the published
tables and the artefact.

## Processing after the join

The three files are joined on the employee, since `id_employee`, `eval_number` and
`code_sondage` hold the same number in three spellings. Notebook 01 and
`scripts/build_frames.py` then replace `id_employee` with the prefix `emp_` followed by the
first sixteen hexadecimal characters of an HMAC-SHA256 digest, stored as `employee_id_anon`,
under a key read from the environment. `eval_number`, its
parsed form `eval_number_int` and `code_sondage` remain in the joined frame, so the original
number stays readable next to its digest. The ten test fixtures leave these three columns out.

The anonymisation is a demonstration, since the rows are fictional. A plain hash of a small,
enumerable set of identifiers can be reversed by hashing every candidate, and the keyed digest
shows the technique that prevents this. [`operations.md`](operations.md) says where the key is
set.

## Licence

IBM published the dataset as sample data, and it is mirrored on Kaggle under the terms of that
page: <https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset>,
consulted on 2026-09-15.

The repository tracks no file under `data/`. The ten rows under `tests/fixtures/` are derived
from the extracts and kept as request payloads for the API tests.
