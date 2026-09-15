"""The correspondence with the IBM dataset is a claim, so it is asserted.

`docs/data-source.md` says the three extracts are IBM's HR Analytics dataset, renamed. That is
the premise of everything the repository publishes: if it is wrong, the base rate is wrong, the
"nobody is described by these rows" is wrong, and the licence section is wrong. These tests pin
the mapping and the signature that established it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from attrition_serving.data import source
from attrition_serving.data.source import (
    COLUMNS,
    DROPPED_UPSTREAM,
    EXPECTED_ROWS,
    EXTRACT_FILES,
    PROFILE,
    columns_of,
    profile,
)

pytestmark = pytest.mark.claim


def test_every_extract_column_names_the_upstream_column_it_came_from() -> None:
    assert len(COLUMNS) == 34
    assert {column.extract for column in COLUMNS} == set(EXTRACT_FILES)
    assert all(column.upstream for column in COLUMNS)


def test_the_two_sides_of_the_correspondence_add_up() -> None:
    """34 columns carried, 3 dropped: IBM ships 35, and the identifier travels three times."""
    upstream = {column.upstream for column in COLUMNS} | set(DROPPED_UPSTREAM)

    assert len(upstream) == 35
    # EmployeeNumber appears in all three extracts, under three spellings.
    identifiers = [c.name for c in COLUMNS if c.upstream == "EmployeeNumber"]
    assert identifiers == ["id_employee", "eval_number", "code_sondage"]


def test_each_translation_is_a_one_to_one_map() -> None:
    """A value mapped onto a value another one already took would merge two categories."""
    for column in COLUMNS:
        if not column.values:
            continue
        targets = list(column.values.values())
        if column.name in {"poste", "domaine_etude"}:
            # `Ressources Humaines` is the job role and the department both, which is IBM's
            # own collision -- `Human Resources` names both there too.
            continue
        assert len(set(targets)) == len(targets), column.name


def test_the_three_extracts_carry_the_columns_the_readers_expect() -> None:
    assert [c.name for c in columns_of("sirh")][:2] == ["id_employee", "age"]
    assert len(columns_of("sirh")) == 12
    assert len(columns_of("eval")) == 10
    assert len(columns_of("sondage")) == 12


def test_the_profile_covers_every_column_it_could_identify() -> None:
    named = {column.name for column in COLUMNS}
    assert set(PROFILE) <= named
    # Only the rendered columns escape it: their value is a spelling of another column,
    # so the signature is checked on the column they are spelled from.
    assert named - set(PROFILE) == {
        "eval_number",
        "code_sondage",
        "augementation_salaire_precedente",
    }


def test_a_frame_that_matches_the_profile_raises_nothing() -> None:
    frame = pd.DataFrame({"genre": ["M"] * 882 + ["F"] * 588})

    assert profile(frame, "genre") == []


def test_a_frame_that_does_not_match_says_which_column_and_how() -> None:
    frame = pd.DataFrame({"genre": ["M"] * 900 + ["F"] * 570})

    problems = profile(frame, "genre")

    assert len(problems) == 1
    assert "genre" in problems[0]


def test_a_range_outside_the_published_one_is_reported() -> None:
    frame = pd.DataFrame({"age": np.arange(18, 75)})

    problems = profile(frame, "age")

    assert any("maximum" in line for line in problems)


def test_a_column_the_profile_does_not_know_is_not_judged() -> None:
    assert profile(pd.DataFrame({"unknown": [1, 2]}), "unknown") == []
    assert profile(pd.DataFrame({"age": [20]}), "absent") == []


def test_the_row_count_and_the_base_rate_are_the_ones_the_readme_publishes() -> None:
    assert EXPECTED_ROWS == 1470
    assert source.EXPECTED_DEPARTURES == 237
    assert round(source.EXPECTED_DEPARTURES / EXPECTED_ROWS, 4) == 0.1612
