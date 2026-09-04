"""The three estimators the protocol scores, each wrapped with its preprocessor.

A dummy for the floor, a logistic regression for the shipped model, a random forest for the
comparison. Each is a `Pipeline`, so cross-validation fits the preprocessing inside the
fold rather than over the whole frame.
"""

from __future__ import annotations

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from attrition_serving.preprocessing import FeatureGroups, build_preprocessor


def make_dummy(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = DummyClassifier(strategy="most_frequent")
    return Pipeline([("preprocess", pre), ("model", clf)])


def make_logreg(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = LogisticRegression(
        max_iter=500,
        class_weight="balanced",  # important imbalance
        solver="saga",  # supports l1/elasticnet too later
        penalty="l2",
    )
    return Pipeline([("preprocess", pre), ("model", clf)])


def make_random_forest(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = RandomForestClassifier(
        n_estimators=400,
        random_state=42,
        class_weight="balanced",
        max_depth=None,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", pre), ("model", clf)])
