FROM python:3.12-slim

WORKDIR /app

# Hugging Face Spaces runs Docker containers with user id 1000
RUN useradd -m -u 1000 appuser

RUN pip install --no-cache-dir uv==0.11.6

# Copy minimal build inputs first (better cache)
COPY --chown=appuser:appuser pyproject.toml uv.lock README.md ./

# Install only what is needed for serving
RUN uv sync --frozen --no-dev --group serve --group db --no-install-project

# Copy code + assets, then install the project itself from the same lockfile. `uv pip
# install` would resolve outside the lock, which is the one thing the previous step took
# care to avoid.
COPY --chown=appuser:appuser src ./src
RUN uv sync --frozen --no-dev --group serve --group db

COPY --chown=appuser:appuser models ./models
COPY --chown=appuser:appuser sql ./sql
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser data/processed/api_test ./data/processed/api_test

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 7860

USER appuser

CMD ["uvicorn", "attrition_serving.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
