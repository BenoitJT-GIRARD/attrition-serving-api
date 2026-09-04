# API — Endpoints, Auth, Examples

## Base URL
- **Local** : `http://localhost:8000`
- **Hugging Face** : `https://huggingface.co/spaces/<owner>/PrjPerso_hr-attrition-mlops`
- **Swagger/OpenAPI** : `/docs`

---

## Authentification
Les endpoints de prédiction requièrent un header :
- `X-API-Key: <API_KEY>`

Sans ce header (ou clé invalide) :
- `401 Unauthorized`

---

## Endpoints

### `GET /health`
**But** : vérifier que l'API est up.

**Exemple** :
```bash
curl http://localhost:8000/health
```

### `POST /predict`
**But** : prédire depuis un payload JSON.

**Payload (IMPORTANT)**
Le payload doit être encapsulé :

```json
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
```

**Exemple curl** :
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"features":{"age":21,"genre":1,"revenu_mensuel":3447,"statut_marital":"Célibataire","departement":"Commercial","poste":"Représentant Commercial","nombre_experiences_precedentes":1,"annee_experience_totale":3,"annees_dans_l_entreprise":3,"annees_dans_le_poste_actuel":2,"satisfaction_employee_environnement":3,"note_evaluation_precedente":3,"niveau_hierarchique_poste":1,"satisfaction_employee_nature_travail":3,"satisfaction_employee_equipe":3,"satisfaction_employee_equilibre_pro_perso":3,"eval_number":"E_669","note_evaluation_actuelle":3,"heure_supplementaires":0,"augementation_salaire_precedente":"11 %","eval_number_int":669,"nombre_participation_pee":0,"nb_formations_suivies":2,"nombre_employee_sous_responsabilite":1,"code_sondage":669,"distance_domicile_travail":22,"niveau_education":1,"domaine_etude":"Entrepreunariat","frequence_deplacement":"Occasionnel","annees_depuis_la_derniere_promotion":1,"annes_sous_responsable_actuel":2,"employee_id_anon":"emp_c8b594649875c70a","changement_poste":1,"proba_chgt_experience_par_an":0.3333333333,"proba_chgt_experience_par_an_adulte":0.3333333333,"ratio_experience_vie_adulte":1.0,"evolution_note":0}}'
```

**Réponse typique** :
```json
{
  "proba_depart": 0.82,
  "prediction": 1,
  "threshold": 0.5,
  "model_version": "local-dev"
}
```

### `POST /predict_by_id/{employee_id}`
**But** : utiliser les features stockées en DB (`employees`).

**Exemple** :
```bash
curl -X POST "http://localhost:8000/predict_by_id/1" \
  -H "X-API-Key: <API_KEY>"
```

### `GET /history`
**But** : historique global des prédictions.

**Exemple** :
```bash
curl "http://localhost:8000/history" -H "X-API-Key: <API_KEY>"
```

### `GET /history/{employee_id}`
**But** : historique d'un employé.

**Exemple** :
```bash
curl "http://localhost:8000/history/1" -H "X-API-Key: <API_KEY>"
```

---

## Exemple Python (httpx)
```python
import os
import httpx

BASE_URL = "http://localhost:8000"
API_KEY = os.environ["API_KEY"]

payload = {
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
        "evolution_note": 0,
    }
}

r = httpx.post(
    f"{BASE_URL}/predict",
    headers={"X-API-Key": API_KEY},
    json=payload,
    timeout=30,
)
print(r.status_code, r.json())
```

---

## Erreurs fréquentes
- **401** : header `X-API-Key` absent/invalide
- **422** : JSON mal formé ou mauvaise structure (oubli de `"features": {...}`)
- **500** : DB inaccessible ou artefact modèle manquant
