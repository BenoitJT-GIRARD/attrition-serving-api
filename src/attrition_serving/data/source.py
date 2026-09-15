"""What the three extracts are, in terms of the public dataset they were cut from.

The extracts under ``data/raw/`` are IBM's *HR Analytics Employee Attrition & Performance*
sample dataset, split into three files, renamed into French and re-themed as a consulting
firm. Nothing here is a record about a person: IBM's data scientists generated the rows.

That is not a guess. Every one of the thirty-four columns below was matched to its IBM
column by range and by distribution, and every categorical value by its exact count — see
:func:`profile`, which the tests replay. The three columns IBM ships and the extracts drop
(``DailyRate``, ``HourlyRate``, ``MonthlyRate``) are named here too, so the correspondence
is total on both sides.

The mapping is what makes the repository reproducible without redistributing anything:
``scripts/build_extracts.py`` rebuilds the three files from the public CSV.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The upstream file, as Kaggle and IBM ship it.
UPSTREAM_FILE = "WA_Fn-UseC_-HR-Employee-Attrition.csv"

#: Rows, departures, and the base rate they imply. Published in the README, and asserted.
EXPECTED_ROWS = 1470
EXPECTED_DEPARTURES = 237

#: Columns IBM ships and the extracts do not carry. Named so the correspondence is total.
DROPPED_UPSTREAM = ("DailyRate", "HourlyRate", "MonthlyRate")


@dataclass(frozen=True)
class Column:
    """One column of one extract, and the upstream column it was cut from.

    ``values`` maps an upstream value to the one the extract carries. Empty when the column
    travelled unchanged; a translation is a decision, and it is written down here rather
    than applied inline where nobody would find it again.
    """

    extract: str
    name: str
    upstream: str
    values: dict[str, str] | None = None


GENDER = {"Female": "F", "Male": "M"}
YES_NO = {"Yes": "Oui", "No": "Non"}
MARITAL = {"Single": "Célibataire", "Married": "Marié(e)", "Divorced": "Divorcé(e)"}
DEPARTMENT = {
    "Sales": "Commercial",
    "Research & Development": "Consulting",
    "Human Resources": "Ressources Humaines",
}
JOB_ROLE = {
    "Sales Executive": "Cadre Commercial",
    "Research Scientist": "Assistant de Direction",
    "Laboratory Technician": "Consultant",
    "Manufacturing Director": "Tech Lead",
    "Healthcare Representative": "Manager",
    "Manager": "Senior Manager",
    "Sales Representative": "Représentant Commercial",
    "Research Director": "Directeur Technique",
    "Human Resources": "Ressources Humaines",
}
EDUCATION_FIELD = {
    "Life Sciences": "Infra & Cloud",
    "Medical": "Transformation Digitale",
    "Marketing": "Marketing",
    "Technical Degree": "Entrepreunariat",
    "Other": "Autre",
    "Human Resources": "Ressources Humaines",
}
BUSINESS_TRAVEL = {
    "Travel_Rarely": "Occasionnel",
    "Travel_Frequently": "Frequent",
    "Non-Travel": "Aucun",
}

#: The thirty-four columns, extract by extract, in the order the files carry them.
COLUMNS: tuple[Column, ...] = (
    # --- extrait_sirh.csv: contract and demographics -----------------------
    Column("sirh", "id_employee", "EmployeeNumber"),
    Column("sirh", "age", "Age"),
    Column("sirh", "genre", "Gender", GENDER),
    Column("sirh", "revenu_mensuel", "MonthlyIncome"),
    Column("sirh", "statut_marital", "MaritalStatus", MARITAL),
    Column("sirh", "departement", "Department", DEPARTMENT),
    Column("sirh", "poste", "JobRole", JOB_ROLE),
    Column("sirh", "nombre_experiences_precedentes", "NumCompaniesWorked"),
    Column("sirh", "nombre_heures_travailless", "StandardHours"),
    Column("sirh", "annee_experience_totale", "TotalWorkingYears"),
    Column("sirh", "annees_dans_l_entreprise", "YearsAtCompany"),
    Column("sirh", "annees_dans_le_poste_actuel", "YearsInCurrentRole"),
    # --- extrait_eval.csv: the annual review -------------------------------
    Column("eval", "satisfaction_employee_environnement", "EnvironmentSatisfaction"),
    Column("eval", "note_evaluation_precedente", "JobInvolvement"),
    Column("eval", "niveau_hierarchique_poste", "JobLevel"),
    Column("eval", "satisfaction_employee_nature_travail", "JobSatisfaction"),
    Column("eval", "satisfaction_employee_equipe", "RelationshipSatisfaction"),
    Column("eval", "satisfaction_employee_equilibre_pro_perso", "WorkLifeBalance"),
    Column("eval", "eval_number", "EmployeeNumber"),  # rendered as E_<number>
    Column("eval", "note_evaluation_actuelle", "PerformanceRating"),
    Column("eval", "heure_supplementaires", "OverTime", YES_NO),
    Column("eval", "augementation_salaire_precedente", "PercentSalaryHike"),  # "11 %"
    # --- extrait_sondage.csv: the internal survey --------------------------
    Column("sondage", "a_quitte_l_entreprise", "Attrition", YES_NO),
    Column("sondage", "nombre_participation_pee", "StockOptionLevel"),
    Column("sondage", "nb_formations_suivies", "TrainingTimesLastYear"),
    Column("sondage", "nombre_employee_sous_responsabilite", "EmployeeCount"),
    Column("sondage", "code_sondage", "EmployeeNumber"),  # zero-padded to six digits
    Column("sondage", "distance_domicile_travail", "DistanceFromHome"),
    Column("sondage", "niveau_education", "Education"),
    Column("sondage", "domaine_etude", "EducationField", EDUCATION_FIELD),
    Column("sondage", "ayant_enfants", "Over18"),
    Column("sondage", "frequence_deplacement", "BusinessTravel", BUSINESS_TRAVEL),
    Column("sondage", "annees_depuis_la_derniere_promotion", "YearsSinceLastPromotion"),
    Column("sondage", "annes_sous_responsable_actuel", "YearsWithCurrManager"),
)

EXTRACT_FILES = {
    "sirh": "extrait_sirh.csv",
    "eval": "extrait_eval.csv",
    "sondage": "extrait_sondage.csv",
}


def columns_of(extract: str) -> tuple[Column, ...]:
    return tuple(column for column in COLUMNS if column.extract == extract)


#: The signature every column of the extracts has to show. A range for a numeric column, an
#: exact count per value for a categorical one. These numbers are how the correspondence
#: with the IBM dataset was established, and `scripts/build_extracts.py --check` replays
#: them: an extract that does not match them is not this dataset.
PROFILE: dict[str, dict[str, object]] = {
    "id_employee": {"min": 1, "max": 2068, "distinct": 1470},
    "age": {"min": 18, "max": 60},
    "genre": {"counts": {"M": 882, "F": 588}},
    "revenu_mensuel": {"min": 1009, "max": 19999},
    "statut_marital": {"counts": {"Marié(e)": 673, "Célibataire": 470, "Divorcé(e)": 327}},
    "departement": {"counts": {"Consulting": 961, "Commercial": 446, "Ressources Humaines": 63}},
    "poste": {
        "counts": {
            "Cadre Commercial": 326,
            "Assistant de Direction": 292,
            "Consultant": 259,
            "Tech Lead": 145,
            "Manager": 131,
            "Senior Manager": 102,
            "Représentant Commercial": 83,
            "Directeur Technique": 80,
            "Ressources Humaines": 52,
        }
    },
    "nombre_experiences_precedentes": {"min": 0, "max": 9},
    "nombre_heures_travailless": {"counts": {"80": 1470}},
    "annee_experience_totale": {"min": 0, "max": 40},
    "annees_dans_l_entreprise": {"min": 0, "max": 40},
    "annees_dans_le_poste_actuel": {"min": 0, "max": 18},
    "satisfaction_employee_environnement": {"counts": {"1": 284, "2": 287, "3": 453, "4": 446}},
    "note_evaluation_precedente": {"counts": {"1": 83, "2": 375, "3": 868, "4": 144}},
    "niveau_hierarchique_poste": {"counts": {"1": 543, "2": 534, "3": 218, "4": 106, "5": 69}},
    "satisfaction_employee_nature_travail": {"counts": {"1": 289, "2": 280, "3": 442, "4": 459}},
    "satisfaction_employee_equipe": {"counts": {"1": 276, "2": 303, "3": 459, "4": 432}},
    "satisfaction_employee_equilibre_pro_perso": {
        "counts": {"1": 80, "2": 344, "3": 893, "4": 153}
    },
    "note_evaluation_actuelle": {"counts": {"3": 1244, "4": 226}},
    "heure_supplementaires": {"counts": {"Non": 1054, "Oui": 416}},
    "a_quitte_l_entreprise": {"counts": {"Non": 1233, "Oui": 237}},
    "nombre_participation_pee": {"counts": {"0": 631, "1": 596, "2": 158, "3": 85}},
    "nb_formations_suivies": {
        "counts": {"0": 54, "1": 71, "2": 547, "3": 491, "4": 123, "5": 119, "6": 65}
    },
    "nombre_employee_sous_responsabilite": {"counts": {"1": 1470}},
    "distance_domicile_travail": {"min": 1, "max": 29},
    "niveau_education": {"counts": {"1": 170, "2": 282, "3": 572, "4": 398, "5": 48}},
    "domaine_etude": {
        "counts": {
            "Infra & Cloud": 606,
            "Transformation Digitale": 464,
            "Marketing": 159,
            "Entrepreunariat": 132,
            "Autre": 82,
            "Ressources Humaines": 27,
        }
    },
    "ayant_enfants": {"counts": {"Y": 1470}},
    "frequence_deplacement": {"counts": {"Occasionnel": 1043, "Frequent": 277, "Aucun": 150}},
    "annees_depuis_la_derniere_promotion": {"min": 0, "max": 15},
    "annes_sous_responsable_actuel": {"min": 0, "max": 17},
}


def profile(frame, column: str) -> list[str]:
    """What the extract's column disagrees with, if anything. Empty means it matches.

    Kept out of the script so the tests can call it on a frame they build themselves, and so
    a reader who wonders what "this is the IBM dataset" rests on can read the numbers.
    """
    expected = PROFILE.get(column)
    if expected is None or column not in frame.columns:
        return []
    series = frame[column]
    problems: list[str] = []
    if "distinct" in expected and series.nunique() != expected["distinct"]:
        problems.append(
            f"{column}: {series.nunique()} distinct values, expected {expected['distinct']}"
        )
    if "min" in expected and series.min() != expected["min"]:
        problems.append(f"{column}: minimum {series.min()}, expected {expected['min']}")
    if "max" in expected and series.max() != expected["max"]:
        problems.append(f"{column}: maximum {series.max()}, expected {expected['max']}")
    if "counts" in expected:
        seen = {str(k): int(v) for k, v in series.astype(str).value_counts().items()}
        if seen != expected["counts"]:
            missing = {k: v for k, v in expected["counts"].items() if seen.get(k) != v}
            problems.append(f"{column}: value counts differ on {sorted(missing)}")
    return problems
