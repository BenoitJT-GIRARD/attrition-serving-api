# API — Endpoints, Auth, Examples

## Base URL

`http://localhost:8000`, with the generated OpenAPI documentation at `/docs`.

The hosted Space this was deployed to has been decommissioned;
[`DEPLOYMENT.md`](DEPLOYMENT.md) describes how it was packaged and what the workflow
pushed, for anyone wanting to stand one up again.

---

## Authentication

Every route except `/health` requires a header:
- `X-API-Key: <API_KEY>`

Without it, or with a key that does not match, the answer is `401 Unauthorized`.

---

## Endpoints

### `GET /health`
**What it answers** — the process is alive. It touches neither the model nor the database, and it needs no key.

**Example:**
```bash
curl http://localhost:8000/health
```

### `POST /predict`
**What it answers** — the probability that this employee leaves, the decision at the served threshold, and the threshold it used.

**The payload is wrapped.** The features go under a `features` key rather than at the top level:

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

**Example:**
```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{"features":{"age":21,"genre":1,"revenu_mensuel":3447,"statut_marital":"Célibataire","departement":"Commercial","poste":"Représentant Commercial","nombre_experiences_precedentes":1,"annee_experience_totale":3,"annees_dans_l_entreprise":3,"annees_dans_le_poste_actuel":2,"satisfaction_employee_environnement":3,"note_evaluation_precedente":3,"niveau_hierarchique_poste":1,"satisfaction_employee_nature_travail":3,"satisfaction_employee_equipe":3,"satisfaction_employee_equilibre_pro_perso":3,"eval_number":"E_669","note_evaluation_actuelle":3,"heure_supplementaires":0,"augementation_salaire_precedente":"11 %","eval_number_int":669,"nombre_participation_pee":0,"nb_formations_suivies":2,"nombre_employee_sous_responsabilite":1,"code_sondage":669,"distance_domicile_travail":22,"niveau_education":1,"domaine_etude":"Entrepreunariat","frequence_deplacement":"Occasionnel","annees_depuis_la_derniere_promotion":1,"annes_sous_responsable_actuel":2,"employee_id_anon":"emp_c8b594649875c70a","changement_poste":1,"proba_chgt_experience_par_an":0.3333333333,"proba_chgt_experience_par_an_adulte":0.3333333333,"ratio_experience_vie_adulte":1.0,"evolution_note":0}}'
```

**A typical response:**
```json
{
  "proba_depart": 0.82,
  "prediction": 1,
  "threshold": 0.1105,
  "model_version": "local-dev"
}
```

### `POST /predict_by_id/{employee_id}`
**What it answers** — the same, for an employee already in the `employees` table, so the caller sends an id instead of thirty-two fields.

**Example:**
```bash
curl -X POST "http://localhost:8000/predict_by_id/1" \
  -H "X-API-Key: <API_KEY>"
```

### `GET /history`
**What it answers** — what has been decided lately, most recent first.

**Example:**
```bash
curl "http://localhost:8000/history" -H "X-API-Key: <API_KEY>"
```

### `GET /history/{employee_id}`
**What it answers** — every decision recorded for one employee.

**Example:**
```bash
curl "http://localhost:8000/history/1" -H "X-API-Key: <API_KEY>"
```

---

## The same call in Python
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

## What each error code means

- **401** — the `X-API-Key` header is missing, or does not match.
- **422** — the JSON is malformed, or the payload is not wrapped: the features go under
  `"features": {...}`, and a request that forgets that wrapper lands here. The body names
  every field it is missing rather than one per round trip.
- **500** — the database is unreachable, or the model artefact is missing. The service
  also refuses to start when the model card carries no threshold: serving an undocumented
  operating point is worse than not serving.
