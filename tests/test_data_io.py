import pandas as pd

from attrition_serving.data_io import anonymize_employee_id, parse_eval_number


def test_parse_eval_number():
    s = pd.Series(["E_1", "E_12", "E_003"])
    out = parse_eval_number(s)
    assert out.tolist() == [1, 12, 3]


def test_anonymize_employee_id_stable():
    s = pd.Series([1, 2, 1])
    key = "unit_test_secret"
    out = anonymize_employee_id(s, key=key)
    assert out.iloc[0] == out.iloc[2]
    assert out.iloc[0] != out.iloc[1]
