"""Draw every published figure from the published tables.

    uv run python scripts/build_figures.py

Each figure reads a CSV under `reports/`, and nothing else. That is deliberate: the tables
are committed, so a reader who has never had the extracts can still rebuild the figures from
a clone and see that they say what the README says they say. Recomputing them from the data
would put the pictures one step further from the numbers beside them.

`scripts/run_evaluation.py` writes the tables. This script never computes a measurement.
"""

from __future__ import annotations

import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from attrition_serving.config import PATHS
from attrition_serving.figure_style import (
    PALETTE,
    apply_style,
    close,
    distribution,
    reference_line,
    save_figure,
    series_colours,
)
from attrition_serving.utils.paths import FIGURES_DIR

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SOURCE = "scripts/build_figures.py"

#: What each model family is called in a figure. The CSV carries the identifier.
MODEL_LABEL = {
    "logreg": "logistic regression",
    "random_forest": "random forest",
    "dummy": "constant baseline",
}

#: What each calibration arm is called. Same reason.
ARM_LABEL = {
    "none": "raw scores",
    "holdout": "isotonic, held-out split",
    "crossfit": "isotonic, cross-fitted — shipped",
}


def _read(name: str) -> pd.DataFrame | None:
    path = PATHS.reports / name
    if not path.exists():
        print(f"[warn] {name} is not under reports/ — run scripts/run_evaluation.py first")
        return None
    return pd.read_csv(path)


def _wilson(successes: np.ndarray, trials: np.ndarray, z: float = 1.96):
    """The Wilson interval for a proportion, which does not fall off the end near 0 or 1.

    The normal approximation puts the HR department's recall interval outside [0, 1] on
    twelve departures, which is the case the table exists to be honest about.
    """
    p = successes / trials
    denominator = 1 + z**2 / trials
    centre = (p + z**2 / (2 * trials)) / denominator
    half = z * np.sqrt(p * (1 - p) / trials + z**2 / (4 * trials**2)) / denominator
    return centre - half, centre + half


def figure_pr_curves(base_rate: float) -> None:
    curves = _read("pr_curves.csv")
    if curves is None:
        return
    names = sorted(curves["model"].unique())
    colours = series_colours([MODEL_LABEL.get(n, n) for n in names])

    figure, axis = plt.subplots(figsize=(7, 5.5))
    for name in names:
        block = curves[curves["model"] == name]
        label = MODEL_LABEL.get(name, name)
        axis.plot(block["recall"], block["precision_mean"], color=colours[label], label=label)
        axis.fill_between(
            block["recall"],
            block["precision_mean"] - block["precision_sem"],
            block["precision_mean"] + block["precision_sem"],
            color=colours[label],
            alpha=0.18,
            linewidth=0,
        )
    reference_line(axis, y=base_rate, label=f"constant baseline, {base_rate:.3f}")
    axis.set_xlabel("recall — share of departures found")
    axis.set_ylabel("precision — share of alerts that were departures")
    axis.set_title("What each model family buys, at every operating point")
    axis.set_ylim(0, 1)
    axis.legend(loc="upper right", frameon=True)
    figure.tight_layout()
    save_figure(
        figure,
        FIGURES_DIR / "pr_curves.png",
        n={"scored rows": 7350, "departures": 1185, "repeats": int(curves["n_repeats"].max())},
        dispersion="band: ±1 standard error over the 5 repeats",
        source=SOURCE,
    )
    close(figure)
    print("[ok] pr_curves.png")


def figure_calibration(base_rate: float) -> None:
    table = _read("calibration.csv")
    if table is None:
        return
    arms = [a for a in ("none", "holdout", "crossfit") if a in set(table["arm"])]
    colours = series_colours([ARM_LABEL[a] for a in arms])

    figure, axis = plt.subplots(figsize=(7, 6))
    reference_line(axis, diagonal=True, label="perfect calibration")
    for arm in arms:
        block = table[table["arm"] == arm]
        label = ARM_LABEL[arm]
        axis.plot(
            block["mean_predicted"],
            block["observed_rate"],
            marker="o",
            markersize=4,
            color=colours[label],
            label=label,
        )
    reference_line(axis, y=base_rate)
    axis.set_xlabel("mean predicted probability, equal-population bins")
    axis.set_ylabel("observed departure rate in the bin")
    axis.set_title("What a returned probability is worth")
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.legend(loc="upper left", frameon=True)
    figure.tight_layout()
    save_figure(
        figure,
        FIGURES_DIR / "calibration.png",
        n={"scored rows": 7350, "departures": 1185, "bins": int(table.groupby("arm").size().max())},
        source=SOURCE,
        note="bins hold equal populations, not equal widths",
    )
    close(figure)
    print("[ok] calibration.png")


def figure_cost_curve(shipped_ratio: int) -> None:
    curve = _read("cost_curve.csv")
    if curve is None:
        return
    names = ["departures caught", "employees flagged", "precision"]
    colours = series_colours(names)

    figure, axis = plt.subplots(figsize=(7, 5))
    axis.plot(
        curve["ratio"], curve["recall_mean"], marker="o", color=colours[names[0]], label=names[0]
    )
    axis.plot(
        curve["ratio"],
        curve["alert_rate_mean"],
        marker="s",
        color=colours[names[1]],
        label=names[1],
    )
    axis.plot(
        curve["ratio"], curve["precision_mean"], marker="^", color=colours[names[2]], label=names[2]
    )
    reference_line(axis, x=shipped_ratio, label=f"shipped, ratio {shipped_ratio}")
    axis.set_xscale("log")
    axis.set_xticks(curve["ratio"])
    axis.set_xticklabels([str(int(r)) for r in curve["ratio"]])
    axis.set_xlabel("wasted conversations one missed departure is worth")
    axis.set_ylabel("share of employees, or of departures")
    axis.set_title("The threshold is a cost decision, and this is the price list")
    axis.set_ylim(0, 1.02)
    axis.legend(loc="upper left", frameon=True)

    for _, row in curve[curve["ratio"] == shipped_ratio].iterrows():
        axis.annotate(
            f"threshold {row['threshold_mean']:.3f}",
            xy=(row["ratio"], row["recall_mean"]),
            xytext=(6, 10),
            textcoords="offset points",
            fontsize=8,
            color=PALETTE["ink"],
        )
    figure.tight_layout()
    save_figure(
        figure,
        FIGURES_DIR / "cost_curve.png",
        n={"scored rows": 7350, "departures": 1185, "folds": 25},
        source=SOURCE,
        note="each point is the mean over the 25 folds",
    )
    close(figure)
    print("[ok] cost_curve.png")


def figure_subgroups() -> None:
    table = _read("subgroups.csv")
    if table is None:
        return
    table = table.dropna(subset=["recall"]).copy()
    caught = (table["recall"] * table["n_positive"]).round().to_numpy()
    low, high = _wilson(caught, table["n_positive"].to_numpy())

    labels = [f"{row.attribute} — {row.group}" for row in table.itertuples()]
    positions = np.arange(len(table))
    colours = series_colours(sorted(table["attribute"].unique()))

    figure, axis = plt.subplots(figsize=(7, 4.8))
    axis.barh(
        positions,
        table["recall"],
        color=[colours[a] for a in table["attribute"]],
        height=0.62,
    )
    axis.errorbar(
        table["recall"],
        positions,
        xerr=[table["recall"] - low, high - table["recall"]],
        fmt="none",
        ecolor=PALETTE["ink"],
        elinewidth=1,
        capsize=3,
    )
    for position, row in zip(positions, table.itertuples(), strict=True):
        axis.text(
            0.015,
            position,
            f"n = {row.n:,}, {row.n_positive} departures",
            va="center",
            fontsize=7.5,
            color=PALETTE["paper"],
        )
    axis.set_yticks(positions)
    axis.set_yticklabels(labels, fontsize=8)
    axis.invert_yaxis()
    axis.set_xlim(0, 1)
    axis.set_xlabel("recall — share of that group's departures the alert list catches")
    axis.set_ylabel("subgroup")
    axis.set_title("Who the alerts land on, at the shipped threshold")
    figure.tight_layout()
    save_figure(
        figure,
        FIGURES_DIR / "subgroups.png",
        # Each attribute partitions the same scored rows, so summing the column would
        # count every employee three times.
        n={
            "scored rows": int(table.groupby("attribute")["n"].sum().max()),
            "attributes": int(table["attribute"].nunique()),
            "groups": len(table),
        },
        dispersion="95 % Wilson interval on the recall of each group",
        source=SOURCE,
    )
    close(figure)
    print("[ok] subgroups.png")


def figure_importance(top_n: int = 15) -> None:
    """One point per fold, the mean as a rule, and the standard error of that mean.

    A bar with a standard deviation said the same thing for a feature whose twenty-five
    folds agree and for one where half of them found nothing: both drew a long whisker. The
    folds are drawn, so the reader sees which of the two they are looking at.
    """
    table = _read("permutation_importance.csv")
    folds = _read("permutation_importance_folds.csv")
    if table is None or folds is None:
        return
    total = len(table)
    table = table.head(top_n).iloc[::-1]
    positions = np.arange(len(table))
    groups = [
        folds.loc[folds["feature"] == name, "importance"].to_numpy() for name in table["feature"]
    ]

    figure, axis = plt.subplots(figsize=(7, 6))
    distribution(
        axis,
        positions,
        groups,
        orient="h",
        colours=[PALETTE["primary"]] * len(groups),
        width=0.55,
        jitter=0.14,
        dot_size=11,
        dot_alpha=0.4,
    )
    reference_line(axis, x=0.0)
    axis.set_yticks(positions)
    axis.set_yticklabels(table["feature"], fontsize=8)
    axis.set_xlabel("average precision lost when the column is shuffled")
    axis.set_ylabel("feature")
    axis.set_title(f"What each feature is worth — the {len(table)} largest of {total}")
    figure.tight_layout()
    save_figure(
        figure,
        FIGURES_DIR / "permutation_importance.png",
        n={"scored rows": 7350, "folds": int(table["n_folds"].max())},
        dispersion="one point per fold; rule: the mean; bar: ±1 standard error of the mean",
        source=SOURCE,
    )
    close(figure)
    print("[ok] permutation_importance.png")


def main() -> int:
    apply_style()
    summary = PATHS.reports / "evaluation_summary.json"
    if not summary.exists():
        print("[fail] reports/evaluation_summary.json is missing — run scripts/run_evaluation.py")
        return 1
    import json

    meta = json.loads(summary.read_text(encoding="utf-8"))
    base_rate = float(meta["protocol"]["prevalence"])
    shipped_ratio = int(meta["protocol"]["shipped_cost_ratio"])

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    figure_pr_curves(base_rate)
    figure_calibration(base_rate)
    figure_cost_curve(shipped_ratio)
    figure_subgroups()
    figure_importance()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
