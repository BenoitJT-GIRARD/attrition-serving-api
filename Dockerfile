FROM python:3.12-slim

# 1. Dossier de travail dans le conteneur
WORKDIR /app

# 2. Installer uv (gestionnaire de dépendances)
RUN pip install --no-cache-dir uv

# 3. Copier les fichiers de dépendances
COPY pyproject.toml uv.lock ./

# 4. Installer UNIQUEMENT ce qui est nécessaire pour servir l’API
#    (pas les notebooks, pas le ML training)
RUN uv sync --frozen --no-dev --group serve --group db

# 5. Copier le code applicatif et les assets nécessaires
COPY src ./src
COPY sql ./sql
COPY scripts ./scripts
COPY models ./models
COPY data/processed/api_test ./data/processed/api_test

# 6. Rendre le code importable
ENV PYTHONPATH=/app/src

# 7. Port standard attendu par Hugging Face
EXPOSE 7860

# 8. Commande de lancement de l’API
CMD ["uv", "run", "uvicorn", "attrition_serving.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
