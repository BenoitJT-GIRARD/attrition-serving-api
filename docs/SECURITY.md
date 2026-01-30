# Security — Secrets, Auth, Data Safety

## 1) Secrets
Aucun secret ne doit être commit :
- `.env.local` ignoré
- `.env.supabase` ignoré
- Secrets CI/HF injectés via settings

**Variables sensibles** :
- `API_KEY`
- `DATABASE_URL`
- Toute clé/token

---

## 2) Authentification
Endpoints de prédiction protégés par API key :
- Header : `X-API-Key: <API_KEY>`

**Objectif** :
- Éviter exposition publique de endpoints ML
- Limiter les abus (POC)

---

## 3) Données RH (sensibles)
- Aucun dataset complet RH n'est seedé en base.
- Seul un sample safe (≤10 lignes) est versionné :
  - `data/processed/api_test/X_test_sample.json`

---

## 4) Traçabilité (audit)
Chaque prédiction est loggée en DB :
- Input exact (`input_payload`)
- `proba_depart`
- `prediction`
- `threshold`
- `model_version`

Cela permet :
- Audit
- Debugging
- Reproductibilité des décisions
