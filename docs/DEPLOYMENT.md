# Deployment — Local / Docker / Hugging Face + CI/CD

## Objectif
Déployer une API FastAPI servant un modèle ML gelé, avec :
- DB PostgreSQL en backend (traçabilité)
- Secrets gérés proprement (pas dans Git)
- CI/CD automatisé (tests + déploiement)

---

## Environnements supportés

### Local (dev)
- API sur `localhost:8000`
- DB via Docker compose sur `localhost:5432`
- Env : `.env.local`

### CI (GitHub Actions)
- DB = service postgres éphémère
- Env injecté via variables CI (pas de dotenv)
- Option `SKIP_DOTENV=1` pour éviter pollution

### Prod (Hugging Face Space)
- API servie via Docker, port `7860`
- DB distante (ex: Supabase) ou autre instance Postgres
- Secrets dans HF "Variables & secrets"

---

## Lancer en local (développement)

### 1) Installer deps
```bash
uv sync --group dev --group db --group serve
```

### 2) Config env
```bash
cp .env.example .env.local
# éditer .env.local
```

### 3) DB
```bash
docker compose up -d
uv run python scripts/db_apply_schema.py
uv run python scripts/db_seed_employees.py
```

### 4) API
```bash
uv run uvicorn attrition_serving.api.main:app --reload --port 8000
```

### 5) Swagger
- http://localhost:8000/docs

---

## Exécution via Docker (simulation prod)

### Build
```bash
docker build -t attrition-api .
```

### Run (port 7860)
Créer un fichier env pour docker (ex: `.env.docker`) contenant au minimum :
- `API_KEY`
- `DATABASE_URL`
- `MODEL_THRESHOLD`
- `MODEL_VERSION`

Puis :
```bash
docker run -d --name attrition_api \
  --env-file .env.docker \
  -p 7860:7860 \
  attrition-api
```

### Ouvrir
- http://localhost:7860/docs

---

## Déploiement Hugging Face Spaces (Docker)

### 1) Space Hugging Face
- Créer un Space "Docker"
- Connecter le repo (ou pousser depuis GitHub Action)

HF lit le `README.md` et son front-matter :
```
sdk: docker
app_port: 7860
```

### 2) Secrets HF (obligatoires)
Dans Space → Settings → Variables & secrets :
- `DATABASE_URL`
- `API_KEY`
- `MODEL_THRESHOLD`
- `MODEL_VERSION`

### 3) Vérifier
- L'app doit démarrer sans erreurs
- `/docs` doit être accessible
- Un appel `/predict` doit fonctionner
- Une ligne doit apparaître dans `predictions`

---

## CI/CD (GitHub Actions → Hugging Face)

### Stratégie Git
- `develop` : intégration continue
- `main` : production (déployée)
- Branches `feature/*`, `fix/*` : travail isolé
- Release taggée : `vX.Y.Z`

### Pipeline attendu
**À chaque push/PR** :
- Checkout
- `uv sync`
- Exécution `pytest`
- (Optionnel) coverage

**Sur push sur main** :
- Déploiement vers HF (push vers le Space)

### Secrets GitHub (exemple)
Dans repo GitHub → Settings → Secrets and variables → Actions :
- `HF_TOKEN`
- `HF_SPACE` (ex: `user/space-name`)

### DB en CI
Les tests d'intégration nécessitent Postgres.
En CI, un service Postgres est lancé et la variable `DATABASE_URL` pointe dessus.

---

## Versioning & traçabilité
`MODEL_VERSION` est loggé dans `predictions`

Pratique recommandée :
- `MODEL_VERSION=v1.0.0` lors d'un tag
- Ou `MODEL_VERSION=main-<sha>` en CI

---

## Smoke tests (check "ça marche")

### En local
- `/health` OK
- `/predict` OK (401 sans clé, 200 avec clé)
- `SELECT COUNT(*) FROM predictions;` augmente après un call

### En prod HF
- `/docs` OK
- Call `/predict` OK
- DB distante reçoit les logs

---

## Rollback (simple)
Si un déploiement est cassé :
- Re-déployer un tag précédent (ou re-push un commit stable sur `main`)
- Garder `MODEL_VERSION` cohérent pour retracer les entrées en DB
