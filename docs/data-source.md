# Where the data comes from

The three files under `data/raw/` are one public dataset, cut in three: IBM's **HR Analytics
Employee Attrition & Performance**, a sample dataset IBM's own data scientists generated and
published. The rows are fictional. No person is described by any of them.

That matters twice. It is the reason nothing here needs to be protected from a reader, and it
is the reason every number this repository publishes can be checked by someone who has never
seen the extracts: the upstream file is public, and the correspondence below is complete.

## What identifies it

| | |
|---|---|
| Rows | 1 470, one per employee |
| Departures | 237, a base rate of 0.1612 |
| Columns the extracts carry | 34 of IBM's 37 |
| Columns IBM ships and the extracts drop | `DailyRate`, `HourlyRate`, `MonthlyRate` |
| Constant columns kept | `nombre_heures_travailless` = 80, `ayant_enfants` = `Y`, `nombre_employee_sous_responsabilite` = 1 |

Those three constants are the fingerprint. IBM's file carries `StandardHours` = 80, `Over18` =
`Y` and `EmployeeCount` = 1 for every one of its 1 470 rows, and nothing else in the public
HR-dataset landscape carries that trio at that row count.

`uv run python scripts/build_extracts.py --check` replays the whole signature, every range and
every value count in the table below, against whatever sits in `data/raw/`, and names the
column that disagrees. Run it before quoting a number.

## Why the columns are in French

The extracts are a repackaging of the dataset: the columns were renamed into French and the
categories re-themed as a consulting firm. `Research & Development` became `Consulting`,
`Life Sciences` became `Infra & Cloud`, and `Sales Executive` became `Cadre Commercial`. Nothing was resampled or perturbed — the value
counts are IBM's, to the row.

Two of the French names are worth a warning, because they say something the column does not.
`nombre_employee_sous_responsabilite` reads as "employees managed" and is `EmployeeCount`, a
constant 1. `nombre_heures_travailless` reads as hours worked and is `StandardHours`, a
constant 80. Both are dropped before the model sees anything.

## The correspondence, column by column

Established by matching each column's range and, for categorical columns, its exact value
counts. `src/attrition_serving/data/source.py` carries the table in code, and the unit tests
replay it.

### `extrait_sirh.csv` — contract and demographics

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

### `extrait_eval.csv` — the annual review

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

The six 1-to-4 columns are told apart by their distributions, which is the only way: IBM ships
five of them with the same range. `JobInvolvement` and `WorkLifeBalance` are the two skewed
ones (83 / 375 / 868 / 144 and 80 / 344 / 893 / 153); the three satisfaction scales are flat.

### `extrait_sondage.csv` — the internal survey

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

## Putting the data back

The extracts are not committed: this repository has no licence that covers redistributing
that particular repackaging of IBM's file. The upstream file does not have that problem, so
what is shipped is the recipe.

```bash
# 1. get WA_Fn-UseC_-HR-Employee-Attrition.csv — IBM sample data, mirrored on Kaggle
# 2. cut it into the three extracts, using the correspondence above
uv run python scripts/build_extracts.py --source path/to/WA_Fn-UseC_-HR-Employee-Attrition.csv
uv run python scripts/build_extracts.py --check
```

The script refuses any value the mapping above does not name, and re-runs the signature check
on what it wrote. From there `scripts/run_evaluation.py` reproduces every published number.

## What is done to it afterwards

The three files are joined on the employee: `id_employee`, `eval_number` and `code_sondage`
are the same number in three spellings. The identifier is then replaced by an HMAC-SHA256
digest keyed from the environment.

That anonymisation is a **demonstration, not a protection**: the rows are fictional, so there
is nothing to protect. It is kept because the plain digest of a small, enumerable identifier
space is reversible by trying every number, and showing the keyed version is the point.
`docs/operations.md` says where the key lives.

## The licence

IBM published the dataset as sample data, and it is mirrored on Kaggle under the terms of that
page: <https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset>,
consulted on 2026-09-15.

This repository redistributes none of it: `data/` holds nothing tracked, and the ten rows
under `tests/fixtures/` are request-shaped payloads for the API tests, derived from the
extracts and kept because ten fictional rows are what a test needs.
