CREATE OR REPLACE VIEW central_clean AS
WITH
sirh AS (
  SELECT * FROM sirh_clean
),
ev AS (
  SELECT * FROM eval_clean
),
sond AS (
  SELECT * FROM sondage_clean
)
SELECT
  -- clés
  s.id_employee,
  e.eval_number_int,
  so.code_sondage::INT AS code_sondage_int,

  -- cible
  so.a_quitte_l_entreprise_int,

  -- sirh
  s.age::INT,
  s.genre,
  s.revenu_mensuel::NUMERIC,
  s.statut_marital,
  s.departement,
  s.poste,
  s.nombre_experiences_precedentes::INT,
  s.annee_experience_totale::NUMERIC,
  s.annees_dans_l_entreprise::NUMERIC,
  s.annees_dans_le_poste_actuel::NUMERIC,

  -- eval
  e.satisfaction_employee_environnement::INT,
  e.satisfaction_employee_nature_travail::INT,
  e.satisfaction_employee_equipe::INT,
  e.satisfaction_employee_equilibre_pro_perso::INT,
  e.note_evaluation_precedente::INT,
  e.note_evaluation_actuelle::INT,
  e.niveau_hierarchique_poste::INT,
  e.heure_supplementaires_int::INT,
  e.augmentation_salaire_precedente_ratio::NUMERIC,

  -- sondage
  so.nombre_participation_pee::INT,
  so.nb_formations_suivies::INT,
  so.nombre_employee_sous_responsabilite::INT,
  so.distance_domicile_travail::NUMERIC,
  so.niveau_education::INT,
  so.domaine_etude,
  so.ayant_enfants,
  so.frequence_deplacement,
  so.annees_depuis_la_derniere_promotion::NUMERIC,
  so.annes_sous_responsable_actuel::NUMERIC

FROM sirh s
JOIN ev e
  ON s.id_employee = e.eval_number_int
JOIN sond so
  ON s.id_employee = (so.code_sondage)::INT;
