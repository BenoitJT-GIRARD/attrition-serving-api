FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --group serve --group db --no-install-project

COPY src ./src
RUN uv pip install -e .

COPY sql ./sql
COPY scripts ./scripts
COPY models ./models
COPY data/processed/api_test ./data/processed/api_test

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "attrition_serving.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
