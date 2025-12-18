from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)


def evaluate_classifier(model, X_train, y_train, X_test, y_test, threshold: float = 0.5) -> dict:
    model.fit(X_train, y_train)

    # proba classe 1
    p_train = model.predict_proba(X_train)[:, 1]
    p_test = model.predict_proba(X_test)[:, 1]

    yhat_train = (p_train >= threshold).astype(int)
    yhat_test = (p_test >= threshold).astype(int)

    out = {
        "threshold": threshold,
        "train_ap": float(average_precision_score(y_train, p_train)),
        "test_ap": float(average_precision_score(y_test, p_test)),
        "train_roc_auc": float(roc_auc_score(y_train, p_train)),
        "test_roc_auc": float(roc_auc_score(y_test, p_test)),
        "train_cm": confusion_matrix(y_train, yhat_train),
        "test_cm": confusion_matrix(y_test, yhat_test),
        "train_report": classification_report(y_train, yhat_train, digits=3),
        "test_report": classification_report(y_test, yhat_test, digits=3),
        "p_test": p_test,
    }
    return out


def plot_precision_recall(y_true, p_hat):
    precision, recall, thr = precision_recall_curve(y_true, p_hat)
    ap = average_precision_score(y_true, p_hat)

    plt.figure()
    plt.plot(recall, precision)
    plt.title(f"Precision-Recall curve (AP={ap:.3f})")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.tight_layout()


def find_threshold_for_recall(y_true, p_hat, target_recall: float = 0.80) -> float:
    precision, recall, thr = precision_recall_curve(y_true, p_hat)
    # thr a une longueur (n-1), recall/precision longueur n
    # on cherche le premier seuil qui atteint recall >= target
    idx = np.where(recall[:-1] >= target_recall)[0]
    if len(idx) == 0:
        return 0.5
    return float(thr[idx[-1]])
