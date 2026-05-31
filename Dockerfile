FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
RUN uv sync --no-dev
ENV PYTHONPATH=/app/src
CMD ["uv", "run", "uvicorn", "ado_swarm.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
