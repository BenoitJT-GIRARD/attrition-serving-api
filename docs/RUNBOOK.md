# Runbook — Checklist Évaluation & Démo

## Objectif
Pouvoir démontrer en 5 minutes :
- API up + Swagger
- Une prédiction fonctionne
- La DB loggue
- Les tests passent + coverage dispo
- CI/CD existe (workflow + secrets)

---

## A) Local — Démarrage DB
```bash
docker compose up -d
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
uv run python scripts/db_smoke_test.py
```

**Preuve** :
```bash
docker exec -it attrition_postgres psql -U attrition -d attrition_serving -c "SELECT COUNT(*) FROM employees;"
```

---

## B) Local — Démarrage API
```bash
uv run uvicorn attrition_serving.api.main:app --reload --port 8000
```

**Preuve** :
- http://localhost:8000/docs

---

## C) Démo — Prediction + logging

### Appel predict (avec API key)
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"features":{"age":21,"genre":1,"revenu_mensuel":3447,"statut_marital":"Célibataire","departement":"Commercial","poste":"Représentant Commercial","nombre_experiences_precedentes":1,"annee_experience_totale":3,"annees_dans_l_entreprise":3,"annees_dans_le_poste_actuel":2,"satisfaction_employee_environnement":3,"note_evaluation_precedente":3,"niveau_hierarchique_poste":1,"satisfaction_employee_nature_travail":3,"satisfaction_employee_equipe":3,"satisfaction_employee_equilibre_pro_perso":3,"eval_number":"E_669","note_evaluation_actuelle":3,"heure_supplementaires":0,"augementation_salaire_precedente":"11 %","eval_number_int":669,"nombre_participation_pee":0,"nb_formations_suivies":2,"nombre_employee_sous_responsabilite":1,"code_sondage":669,"distance_domicile_travail":22,"niveau_education":1,"domaine_etude":"Entrepreunariat","frequence_deplacement":"Occasionnel","annees_depuis_la_derniere_promotion":1,"annes_sous_responsable_actuel":2,"employee_id_anon":"emp_c8b594649875c70a","changement_poste":1,"proba_chgt_experience_par_an":0.3333333333,"proba_chgt_experience_par_an_adulte":0.3333333333,"ratio_experience_vie_adulte":1.0,"evolution_note":0}}'
```

### Vérifier DB
```bash
docker exec -it attrition_postgres psql -U attrition -d attrition_serving \
  -c "SELECT id, created_at, proba_depart, prediction FROM predictions ORDER BY created_at DESC LIMIT 5;"
```

---

## D) Tests + couverture
```bash
uv run pytest -q
uv run pytest --cov=src --cov-report=term-missing --cov-report=html:reports/coverage_html
```

---

## E) Déploiement HF (preuve)
- Ouvrir : https://huggingface.co/spaces/<owner>/PrjPerso_hr-attrition-mlops
- Faire un call `/predict` (avec API key)
- Vérifier DB distante (Supabase) : `COUNT predictions` augmente

---

## F) CI/CD (preuve)
- Le fichier workflow `.github/workflows/<...>.yml`
- Run "green" dans GitHub Actions
