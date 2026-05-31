set dotenv-load := true
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

_default:
  just --list

setup:
  uv sync --all-extras --dev
  prek install

format:
  uv run ruff format src tests
  uv run ruff check --fix src tests

lint:
  uv run ruff check src tests

typecheck:
  uv run ty check

test:
  uv run pytest tests/unit

test-integration:
  uv run pytest tests/integration

eval-agent agent:
  uv run python -m ado_swarm.agents.{{agent}}.eval --model-profile fake --output .artifacts/evals/{{agent}}.json

eval-agents:
  uv run ado-swarm eval-agents --model-profile fake --output .artifacts/evals/agents.json

check: lint typecheck test eval-agents

up:
  docker compose up -d --build

down:
  docker compose down

reset:
  docker compose down -v
  docker compose up -d --build

logs service="":
  if [ -z "{{service}}" ]; then docker compose logs -f; else docker compose logs -f {{service}}; fi

migrate:
  uv run python -m ado_swarm.storage.migrations apply

api:
  uv run uvicorn ado_swarm.api.app:app --reload --host 0.0.0.0 --port 8000

worker-supervisor:
  uv run python -m ado_swarm.workers.supervisor_worker

worker-agent:
  uv run python -m ado_swarm.workers.agent_worker

smoke:
  uv run ado-swarm smoke
