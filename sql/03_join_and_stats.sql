-- =========================
-- Join + descriptive stats
-- =========================

WITH
sirh AS (
  SELECT * FROM sirh_clean
),
ev AS (
  SELECT * FROM eval_clean
),
sond AS (
  SELECT * FROM sondage_clean
),
central AS (
  SELECT
    s.id_employee,
    s.age,
    s.genre,
    s.revenu_mensuel,
    s.statut_marital,
    s.departement,
    s.poste,
    s.nombre_experiences_precedentes,
    s.annee_experience_totale,
    s.annees_dans_l_entreprise,
    s.annees_dans_le_poste_actuel,

    e.satisfaction_employee_environnement,
    e.satisfaction_employee_nature_travail,
    e.satisfaction_employee_equipe,
    e.satisfaction_employee_equilibre_pro_perso,
    e.note_evaluation_precedente,
    e.note_evaluation_actuelle,
    e.niveau_hierarchique_poste,
    e.heure_supplementaires_int,
    e.augmentation_salaire_precedente_ratio,

    so.a_quitte_l_entreprise_int,
    so.distance_domicile_travail,
    so.niveau_education,
    so.domaine_etude,
    so.frequence_deplacement,
    so.annees_depuis_la_derniere_promotion,
    so.annes_sous_responsable_actuel,
    so.nb_formations_suivies,
    so.nombre_participation_pee,
    so.nombre_employee_sous_responsabilite
  FROM sirh s
  JOIN ev e
    ON s.id_employee = e.eval_number_int
  JOIN sond so
    ON s.id_employee = (so.code_sondage)::INT
)

SELECT
  a_quitte_l_entreprise_int AS a_quitte,
  COUNT(*) AS n,
  AVG(age::NUMERIC) AS age_mean,
  STDDEV_SAMP(age::NUMERIC) AS age_std,
  AVG(revenu_mensuel::NUMERIC) AS revenu_mean,
  STDDEV_SAMP(revenu_mensuel::NUMERIC) AS revenu_std,
  AVG(augmentation_salaire_precedente_ratio) AS augm_ratio_mean
FROM central
GROUP BY a_quitte_l_entreprise_int
ORDER BY a_quitte_l_entreprise_int;
