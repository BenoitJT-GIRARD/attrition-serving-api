"""What the scripts do, without the data they normally read.

`build_extracts.build` is the one that matters: it is the recipe `docs/data-source.md`
publishes, so a reader with the public IBM file gets the same three extracts this repository
was built on. Everything it does is a declared mapping, which makes it testable on six rows.

The figure builders are here too. They read a published CSV and write a PNG, and the style
module refuses a figure whose axes are unlabelled or whose sample size is undeclared -- so
calling them is how that refusal is exercised.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import replace

import pandas as pd
import pytest

from attrition_serving.data.source import EXTRACT_FILES

build_extracts = importlib.import_module("build_extracts")
build_figures = importlib.import_module("build_figures")


@pytest.fixture()
def upstream() -> pd.DataFrame:
    """Six rows shaped like IBM's file, with one value from every translated category."""
    return pd.DataFrame(
        {
            "EmployeeNumber": [1, 2, 4, 5, 7, 8],
            "Age": [41, 49, 37, 33, 27, 32],
            "Gender": ["Female", "Male", "Male", "Female", "Male", "Male"],
            "MonthlyIncome": [5993, 5130, 2090, 2909, 3468, 3068],
            "MaritalStatus": ["Single", "Married", "Single", "Married", "Married", "Divorced"],
            "Department": [
                "Sales",
                "Research & Development",
                "Research & Development",
                "Research & Development",
                "Research & Development",
                "Human Resources",
            ],
            "JobRole": [
                "Sales Executive",
                "Research Scientist",
                "Laboratory Technician",
                "Research Scientist",
                "Laboratory Technician",
                "Human Resources",
            ],
            "NumCompaniesWorked": [8, 1, 6, 1, 9, 0],
            "StandardHours": [80] * 6,
            "TotalWorkingYears": [8, 10, 7, 8, 6, 8],
            "YearsAtCompany": [6, 10, 0, 8, 2, 7],
            "YearsInCurrentRole": [4, 7, 0, 7, 2, 7],
            "EnvironmentSatisfaction": [2, 3, 4, 4, 1, 4],
            "JobInvolvement": [3, 2, 2, 3, 3, 3],
            "JobLevel": [2, 2, 1, 1, 1, 1],
            "JobSatisfaction": [4, 2, 3, 3, 2, 4],
            "RelationshipSatisfaction": [1, 4, 2, 3, 4, 3],
            "WorkLifeBalance": [1, 3, 3, 3, 2, 2],
            "PerformanceRating": [3, 4, 3, 3, 3, 3],
            "OverTime": ["Yes", "No", "Yes", "Yes", "No", "No"],
            "PercentSalaryHike": [11, 23, 15, 11, 12, 13],
            "Attrition": ["Yes", "No", "Yes", "No", "No", "No"],
            "StockOptionLevel": [0, 1, 0, 0, 1, 3],
            "TrainingTimesLastYear": [0, 3, 3, 3, 2, 5],
            "EmployeeCount": [1] * 6,
            "DistanceFromHome": [1, 8, 2, 3, 2, 2],
            "Education": [2, 1, 2, 4, 1, 2],
            "EducationField": [
                "Life Sciences",
                "Life Sciences",
                "Other",
                "Life Sciences",
                "Medical",
                "Technical Degree",
            ],
            "Over18": ["Y"] * 6,
            "BusinessTravel": [
                "Travel_Rarely",
                "Travel_Frequently",
                "Travel_Rarely",
                "Travel_Frequently",
                "Travel_Rarely",
                "Non-Travel",
            ],
            "YearsSinceLastPromotion": [0, 1, 0, 3, 2, 3],
            "YearsWithCurrManager": [5, 7, 0, 0, 2, 7],
            "DailyRate": [1102, 279, 1373, 1392, 591, 1005],
            "HourlyRate": [94, 61, 92, 56, 40, 79],
            "MonthlyRate": [19479, 24907, 2396, 23159, 16632, 11864],
        }
    )


def test_the_three_extracts_come_out_with_the_columns_the_mapping_names(upstream) -> None:
    extracts = build_extracts.build(upstream)

    assert set(extracts) == set(EXTRACT_FILES)
    assert list(extracts["sirh"].columns)[:3] == ["id_employee", "age", "genre"]
    assert all(len(frame) == 6 for frame in extracts.values())


def test_every_translated_value_comes_out_in_the_language_the_extracts_use(upstream) -> None:
    extracts = build_extracts.build(upstream)

    assert list(extracts["sirh"]["genre"]) == ["F", "M", "M", "F", "M", "M"]
    assert extracts["sirh"]["departement"].iloc[0] == "Commercial"
    assert extracts["sirh"]["statut_marital"].iloc[1] == "Marié(e)"
    assert extracts["sondage"]["domaine_etude"].iloc[0] == "Infra & Cloud"
    assert extracts["sondage"]["frequence_deplacement"].iloc[5] == "Aucun"
    assert extracts["eval"]["heure_supplementaires"].iloc[0] == "Oui"


def test_the_identifier_is_rendered_three_ways_from_one_column(upstream) -> None:
    extracts = build_extracts.build(upstream)

    assert extracts["sirh"]["id_employee"].iloc[0] == 1
    assert extracts["eval"]["eval_number"].iloc[0] == "E_1"
    assert extracts["sondage"]["code_sondage"].iloc[0] == "000001"


def test_the_pay_rise_is_rendered_the_way_the_extract_carries_it(upstream) -> None:
    assert (
        build_extracts.build(upstream)["eval"]["augementation_salaire_precedente"].iloc[0] == "11 %"
    )


def test_a_value_the_mapping_does_not_name_stops_the_build(upstream) -> None:
    """A new category would otherwise become a missing value, silently, in a whole column."""
    unknown = upstream.assign(Department=["Marketing"] + list(upstream["Department"][1:]))

    with pytest.raises(SystemExit, match="Department"):
        build_extracts.build(unknown)


def test_a_source_file_missing_a_column_stops_the_build(upstream) -> None:
    with pytest.raises(SystemExit, match="OverTime"):
        build_extracts.build(upstream.drop(columns=["OverTime"]))


def test_the_check_says_which_file_is_not_there(tmp_path) -> None:
    problems = build_extracts.check(tmp_path)

    assert len(problems) == 3
    assert all("is not there" in line for line in problems)


def test_the_check_refuses_a_file_with_the_wrong_row_count(tmp_path, upstream) -> None:
    for extract, frame in build_extracts.build(upstream).items():
        frame.to_csv(tmp_path / EXTRACT_FILES[extract], index=False, encoding="utf-8")

    problems = build_extracts.check(tmp_path)

    assert any("6 rows, expected 1470" in line for line in problems)


def test_a_figure_is_written_from_the_published_table(tmp_path, monkeypatch) -> None:
    """The style module refuses an unlabelled figure; writing one is how that is exercised."""
    reports = tmp_path / "reports"
    reports.mkdir()
    pd.DataFrame(
        {
            "ratio": [1, 8],
            "threshold_mean": [0.5, 0.11],
            "threshold_sd": [0.1, 0.02],
            "recall_mean": [0.36, 0.78],
            "recall_sd": [0.04, 0.05],
            "precision_mean": [0.77, 0.35],
            "precision_sd": [0.04, 0.05],
            "alert_rate_mean": [0.08, 0.37],
            "alert_rate_sd": [0.01, 0.10],
        }
    ).to_csv(reports / "cost_curve.csv", index=False)

    monkeypatch.setattr(build_figures, "PATHS", replace(build_figures.PATHS, reports=reports))
    monkeypatch.setattr(build_figures, "FIGURES_DIR", tmp_path / "figures")
    build_figures.apply_style()
    build_figures.figure_cost_curve(shipped_ratio=8)

    written = tmp_path / "figures" / "cost_curve.png"
    assert written.exists()
    manifest = json.loads((tmp_path / "figures" / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = manifest["images"]["cost_curve.png"]
    assert entry["source"] == "scripts/build_figures.py"
    assert "7350" in entry["n"]
    assert all(axis["x"] and axis["y"] for axis in entry["axes"])


def test_a_figure_whose_table_is_missing_says_so_and_writes_nothing(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(build_figures, "PATHS", replace(build_figures.PATHS, reports=tmp_path))
    monkeypatch.setattr(build_figures, "FIGURES_DIR", tmp_path / "figures")

    build_figures.figure_subgroups()

    assert "run scripts/run_evaluation.py first" in capsys.readouterr().out
    assert not (tmp_path / "figures").exists()


def test_the_wilson_interval_stays_inside_the_unit_range() -> None:
    """The normal approximation leaves it on twelve events, which is the HR group's case."""
    import numpy as np

    low, high = build_figures._wilson(np.array([12.0]), np.array([12.0]))

    assert low >= 0.0
    assert high <= 1.0
