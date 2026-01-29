-- =========================
-- Clean views (staging -> clean)
-- =========================

-- 1) EVAL : clé + oui/non + % -> ratio
CREATE OR REPLACE VIEW eval_clean AS
WITH base AS (
  SELECT
    *,
    CAST(REPLACE(eval_number, 'E_', '') AS INTEGER) AS eval_number_int,
    CASE LOWER(TRIM(heure_supplementaires))
      WHEN 'oui' THEN 1
      WHEN 'non' THEN 0
      ELSE NULL
    END AS heure_supplementaires_int,
    CASE
      WHEN augementation_salaire_precedente IS NULL THEN NULL
      ELSE
        NULLIF(REPLACE(TRIM(augementation_salaire_precedente), '%', ''), '')::NUMERIC / 100.0
    END AS augmentation_salaire_precedente_ratio
  FROM eval_raw
)
SELECT * FROM base;


-- 2) SONDAGE : cible oui/non -> int
CREATE OR REPLACE VIEW sondage_clean AS
WITH base AS (
  SELECT
    *,
    CASE LOWER(TRIM(a_quitte_l_entreprise))
      WHEN 'oui' THEN 1
      WHEN 'non' THEN 0
      ELSE NULL
    END AS a_quitte_l_entreprise_int
  FROM sondage_raw
)
SELECT * FROM base;


-- 3) SIRH : ici pas d'augmentation, juste la table "pro"
CREATE OR REPLACE VIEW sirh_clean AS
WITH base AS (
  SELECT
    *
  FROM sirh_raw
)
SELECT * FROM base;
