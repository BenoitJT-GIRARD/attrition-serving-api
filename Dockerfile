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

# The served artefacts, and nothing else: no scripts, no SQL, no fixtures. What an operator
# runs, they run from a checkout.
COPY --chown=appuser:appuser models ./models

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 7860

# The liveness probe is `/health`, and it deliberately needs neither the artefact nor the
# database. Without a probe at all, an orchestrator counts a silent container as running.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/health', timeout=2)"

USER appuser

CMD ["uvicorn", "attrition_serving.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
