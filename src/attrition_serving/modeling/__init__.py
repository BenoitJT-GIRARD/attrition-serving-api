"""Fitting, tuning, and the protocol that decides what a score is worth.

`protocol` is the one to read: it holds the cross-validated evaluation, the threshold
selection, the cost curve and the calibration, and every published figure comes through it.
`models` and `tuning` only build estimators for it to score.
"""
