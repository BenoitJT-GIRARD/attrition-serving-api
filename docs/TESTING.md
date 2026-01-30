# Testing — Strategy, Commands, Coverage

## Objectif
Garantir que le serving est fiable :
- Sécurité (API key)
- Validation (Pydantic)
- Cohérence train/serve (features attendues)
- Intégration API ↔ DB (logging systématique)
- Reproductibilité (env isolé)

---

## Lancer les tests
```bash
uv run pytest -q
```

---

## Couverture (pytest-cov)
```bash
uv run pytest --cov=src --cov-report=term-missing --cov-report=html:reports/coverage_html
```

**Résultat HTML** :
- `reports/coverage_html/index.html`
