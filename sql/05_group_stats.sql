SELECT
  a_quitte_l_entreprise_int AS a_quitte,
  COUNT(*) AS n,

  AVG(age) AS age_mean,
  STDDEV_SAMP(age) AS age_std,

  AVG(revenu_mensuel) AS revenu_mean,
  STDDEV_SAMP(revenu_mensuel) AS revenu_std,

  AVG(distance_domicile_travail) AS dist_mean,
  STDDEV_SAMP(distance_domicile_travail) AS dist_std,

  AVG(annees_dans_l_entreprise) AS tenure_mean,
  STDDEV_SAMP(annees_dans_l_entreprise) AS tenure_std,

  AVG(annees_dans_le_poste_actuel) AS poste_mean,
  STDDEV_SAMP(annees_dans_le_poste_actuel) AS poste_std,

  AVG(annee_experience_totale) AS exp_mean,
  STDDEV_SAMP(annee_experience_totale) AS exp_std,

  AVG(augmentation_salaire_precedente_ratio) AS augm_ratio_mean

FROM central_clean
GROUP BY a_quitte_l_entreprise_int
ORDER BY a_quitte_l_entreprise_int;
