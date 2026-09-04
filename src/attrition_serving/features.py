from __future__ import annotations

import numpy as np
import pandas as pd

from attrition_serving.cleaning import (
    drop_constant_columns,
    percent_to_ratio,
    safe_divide,
    yes_no_to_int,
)


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # --- Binary mappings
    if "a_quitte_l_entreprise" in out.columns:
        out["a_quitte_l_entreprise"] = yes_no_to_int(out["a_quitte_l_entreprise"])

    if "heure_supplementaires" in out.columns:
        out["heure_supplementaires"] = yes_no_to_int(out["heure_supplementaires"])

    # --- Percent to ratio
    if "augmentation_salaire_precedente" in out.columns:
        out["augmentation_salaire_precedente"] = percent_to_ratio(
            out["augmentation_salaire_precedente"]
        )

    # gender: "F"/"M" to 0/1 when the source has not already done it
    if "genre" in out.columns:
        g = out["genre"].astype(str).str.strip().str.upper()
        if set(g.dropna().unique()).issubset({"F", "M"}):
            out["genre"] = g.map({"F": 0, "M": 1}).astype("Int64")

    # Constant columns carry no information a model can use, and one-hot encoding them
    # adds a column that is always 1. Dropped by name-safe lookup.
    out = drop_constant_columns(out, candidates=["nombre_heures_travailless", "ayant_enfants"])

    # --- New feature: changement de poste
    if {"annees_dans_l_entreprise", "annees_dans_le_poste_actuel"}.issubset(out.columns):
        out["changement_poste"] = (
            pd.to_numeric(out["annees_dans_l_entreprise"], errors="coerce")
            > pd.to_numeric(out["annees_dans_le_poste_actuel"], errors="coerce")
        ).astype("Int64")

    # normalised ratios
    # The source spells this column two ways depending on the extract, so both are
    # accepted rather than one being assumed.
    exp_col = None
    for cand in ["nombre_experiences_precedents", "nombre_experiences_precedentes"]:
        if cand in out.columns:
            exp_col = cand
            break

    if exp_col and "annee_experience_totale" in out.columns:
        out["proba_chgt_experience_par_an"] = safe_divide(
            out[exp_col], out["annee_experience_totale"]
        )

    if exp_col and "age" in out.columns:
        adult_years = pd.to_numeric(out["age"], errors="coerce") - 18
        out["proba_chgt_experience_par_an_adulte"] = safe_divide(out[exp_col], adult_years)

    if "annee_experience_totale" in out.columns and "age" in out.columns:
        adult_years = pd.to_numeric(out["age"], errors="coerce") - 18
        out["ratio_experience_vie_adulte"] = safe_divide(
            out["annee_experience_totale"], adult_years
        )

    # --- Evolution note
    if {"note_evaluation_actuelle", "note_evaluation_precedente"}.issubset(out.columns):
        out["evolution_note"] = pd.to_numeric(
            out["note_evaluation_actuelle"], errors="coerce"
        ) - pd.to_numeric(out["note_evaluation_precedente"], errors="coerce")

    return out


def compute_incoherence_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Count the rows whose career history contradicts itself.

    Two checks, both on relations that must hold by construction. They are reported as a
    count and a share rather than repaired: a row where total experience is shorter than
    tenure is a data problem, and silently fixing it would hide how often the sources
    disagree.
    """
    out = {}

    # 1. total experience >= tenure at the company >= years in the current role
    needed = {"annee_experience_totale", "annees_dans_l_entreprise", "annees_dans_le_poste_actuel"}
    if needed.issubset(df.columns):
        a = pd.to_numeric(df["annee_experience_totale"], errors="coerce")
        b = pd.to_numeric(df["annees_dans_l_entreprise"], errors="coerce")
        c = pd.to_numeric(df["annees_dans_le_poste_actuel"], errors="coerce")
        ok = (a >= b) & (b >= c)
        out["incoherence_hierarchy_count"] = float((~ok).sum())
        out["incoherence_hierarchy_ratio"] = float((~ok).mean())

    # 2. with no previous employer, total experience and tenure should coincide
    exp_col = None
    for cand in ["nombre_experiences_precedents", "nombre_experiences_precedentes"]:
        if cand in df.columns:
            exp_col = cand
            break

    if exp_col and {"annee_experience_totale", "annees_dans_l_entreprise"}.issubset(df.columns):
        exp_prev = pd.to_numeric(df[exp_col], errors="coerce")
        a = pd.to_numeric(df["annee_experience_totale"], errors="coerce")
        b = pd.to_numeric(df["annees_dans_l_entreprise"], errors="coerce")
        mask = exp_prev == 0
        gap = a - b
        # The share of rows where the gap is positive, which is the direction that
        # indicates undeclared previous experience.
        out["gap_exp_minus_tenure_when_no_prev_ratio"] = (
            float((gap[mask] > 0).mean()) if mask.any() else np.nan
        )

    return out
