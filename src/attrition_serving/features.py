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

    # --- genre : "F"/"M" -> 0/1 (si nécessaire)
    if "genre" in out.columns:
        g = out["genre"].astype(str).str.strip().str.upper()
        if set(g.dropna().unique()).issubset({"F", "M"}):
            out["genre"] = g.map({"F": 0, "M": 1}).astype("Int64")

    # --- Drop constants (as requested, but safe if names differ)
    out = drop_constant_columns(out, candidates=["nombre_heures_travailless", "ayant_enfants"])

    # --- New feature: changement de poste
    if {"annees_dans_l_entreprise", "annees_dans_le_poste_actuel"}.issubset(out.columns):
        out["changement_poste"] = (
            pd.to_numeric(out["annees_dans_l_entreprise"], errors="coerce")
            > pd.to_numeric(out["annees_dans_le_poste_actuel"], errors="coerce")
        ).astype("Int64")

    # --- Probabilités/ratios normalisés
    # ⚠️ Tes colonnes peuvent s'appeler "nombre_experiences_precedents" ou "...precedentes"
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
    """
    Retourne des métriques simples (n et ratio) sur incohérences demandées.
    """
    out = {}

    # incohérence 1: exp_totale >= ancienneté >= années poste
    needed = {"annee_experience_totale", "annees_dans_l_entreprise", "annees_dans_le_poste_actuel"}
    if needed.issubset(df.columns):
        a = pd.to_numeric(df["annee_experience_totale"], errors="coerce")
        b = pd.to_numeric(df["annees_dans_l_entreprise"], errors="coerce")
        c = pd.to_numeric(df["annees_dans_le_poste_actuel"], errors="coerce")
        ok = (a >= b) & (b >= c)
        out["incoherence_hierarchy_count"] = float((~ok).sum())
        out["incoherence_hierarchy_ratio"] = float((~ok).mean())

    # incohérence 2: si 0 expériences précédentes => exp_totale - ancienneté devrait être ~0
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
        # proxy: proportion > 0 (tu as demandé “ratio > 0”)
        out["gap_exp_minus_tenure_when_no_prev_ratio"] = (
            float((gap[mask] > 0).mean()) if mask.any() else np.nan
        )

    return out
