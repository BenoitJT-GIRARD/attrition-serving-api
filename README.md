## Database schema (serving)

```mermaid
erDiagram
  EMPLOYEES {
    int employee_id PK
    jsonb features
    timestamptz created_at
  }

  PREDICTIONS {
    bigint id PK
    timestamptz created_at
    int employee_id FK
    jsonb input_payload
    float proba_depart
    int prediction
    float threshold
    string model_version
  }

  EMPLOYEES ||--o{ PREDICTIONS : "employee_id"




## Environment configuration

This project uses environment-specific `.env` files:

- `.env.example`: reference configuration (versioned)
- `.env.local`: local development (ignored)
- `.env.supabase`: Supabase deployment (ignored)

Only `.env.example` is committed to version control.








uv run uvicorn attrition_serving.api.main:app --reload --host 0.0.0.0 --port 8000

http://localhost:8000/docs

example :
{
  "features": {
    "age": 21,
    "genre": 1,
    "revenu_mensuel": 3447,
    "statut_marital": "Célibataire",
    "departement": "Commercial",
    "poste": "Représentant Commercial",
    "nombre_experiences_precedentes": 1,
    "annee_experience_totale": 3,
    "annees_dans_l_entreprise": 3,
    "annees_dans_le_poste_actuel": 2,
    "satisfaction_employee_environnement": 3,
    "note_evaluation_precedente": 3,
    "niveau_hierarchique_poste": 1,
    "satisfaction_employee_nature_travail": 3,
    "satisfaction_employee_equipe": 3,
    "satisfaction_employee_equilibre_pro_perso": 3,
    "eval_number": "E_669",
    "note_evaluation_actuelle": 3,
    "heure_supplementaires": 0,
    "augementation_salaire_precedente": "11 %",
    "eval_number_int": 669,
    "nombre_participation_pee": 0,
    "nb_formations_suivies": 2,
    "nombre_employee_sous_responsabilite": 1,
    "code_sondage": 669,
    "distance_domicile_travail": 22,
    "niveau_education": 1,
    "domaine_etude": "Entrepreunariat",
    "frequence_deplacement": "Occasionnel",
    "annees_depuis_la_derniere_promotion": 1,
    "annes_sous_responsable_actuel": 2,
    "employee_id_anon": "emp_c8b594649875c70a",
    "changement_poste": 1,
    "proba_chgt_experience_par_an": 0.3333333333,
    "proba_chgt_experience_par_an_adulte": 0.3333333333,
    "ratio_experience_vie_adulte": 1.0,
    "evolution_note": 0
  }
}






docker exec -it attrition_postgres psql -U attrition -d attrition_serving -c "SELECT id, created_at, employee_id, proba_depart, prediction FROM predictions ORDER BY created_at DESC LIMIT 5;"
