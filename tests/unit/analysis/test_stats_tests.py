"""The univariate comparison published in the data dossier.

Twenty columns compared without a correction hand back one significant result by chance,
so the table carries a corrected p-value beside the raw one and the test it used.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from attrition_serving.analysis.stats_tests import compare_groups_univariate


def test_a_univariate_comparison_names_its_test_and_corrects_for_multiplicity() -> None:
    """Twenty columns and no correction would hand back one significant result by chance."""
    rng = np.random.default_rng(5)
    frame = pd.DataFrame(
        {
            "a_quitte_l_entreprise": [0] * 40 + [1] * 40,
            "separates": np.concatenate([rng.normal(0, 1, 40), rng.normal(3, 1, 40)]),
            "does_not": rng.normal(0, 1, 80),
        }
    )

    table = compare_groups_univariate(
        frame, target="a_quitte_l_entreprise", cols=["separates", "does_not"]
    )

    assert len(table) == 2
    assert "test" in table.columns
    row = table.set_index("feature").loc["separates"]
    assert row["p_value"] < 0.01
    assert table.set_index("feature").loc["does_not", "p_value"] > 0.05
    assert "p_value_fdr" in table.columns


def test_a_column_the_frame_does_not_have_is_skipped_and_not_invented() -> None:
    frame = pd.DataFrame({"a_quitte_l_entreprise": [0, 1] * 8, "present": range(16)})

    table = compare_groups_univariate(
        frame, target="a_quitte_l_entreprise", cols=["present", "absent"]
    )

    assert list(table["feature"]) == ["present"]
