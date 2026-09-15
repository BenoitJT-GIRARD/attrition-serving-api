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

from attrition_serving.config import SETTINGS
from attrition_serving.preprocessing import FeatureGroups, build_preprocessor


def make_dummy(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = DummyClassifier(strategy="most_frequent")
    return Pipeline([("preprocess", pre), ("model", clf)])


def make_logreg(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = LogisticRegression(
        max_iter=500,
        # 237 departures against 1,233 stays. Without this the model learns the majority
        # class and the scores rank badly; with it they rank well and stop being
        # probabilities, which is what the calibration arms are for.
        class_weight="balanced",
        solver="saga",
        # Ridge, spelled the way scikit-learn 1.8 asks for it: `penalty="l2"` is deprecated
        # in 1.8 and gone in 1.10, and a warning printed on every fit stops being read
        # by the third run.
        l1_ratio=0.0,
        # `saga` is stochastic. Without a seed the published threshold moved between two
        # runs of the same script on the same data -- 0.508 and 0.545 at a cost ratio of
        # one -- and every table in the repository was a draw nobody could reproduce.
        random_state=SETTINGS.random_state,
    )
    return Pipeline([("preprocess", pre), ("model", clf)])


def make_random_forest(groups: FeatureGroups) -> Pipeline:
    pre = build_preprocessor(groups)
    clf = RandomForestClassifier(
        n_estimators=400,
        random_state=SETTINGS.random_state,
        class_weight="balanced",
        max_depth=None,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", pre), ("model", clf)])
