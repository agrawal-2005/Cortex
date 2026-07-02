.PHONY: up down build logs test migrate migrate-create shell db-shell lint format clean

# ── Docker ──────────────────────────────────────────────────────
up:
	docker compose up -d

up-build:
	docker compose up -d --build

down:
	docker compose down

down-clean:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

# ── Database Migrations ─────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	@read -p "Migration message: " msg; \
	docker compose exec backend alembic revision --autogenerate -m "$$msg"

migrate-downgrade:
	docker compose exec backend alembic downgrade -1

migrate-history:
	docker compose exec backend alembic history

# ── Testing ─────────────────────────────────────────────────────
test:
	docker compose exec backend python -m pytest tests/ -v

test-cov:
	docker compose exec backend python -m pytest tests/ -v --cov=backend --cov-report=term-missing

test-local:
	python -m pytest tests/ -v

# ── Development ─────────────────────────────────────────────────
shell:
	docker compose exec backend bash

db-shell:
	docker compose exec db psql -U cortex -d cortex

redis-shell:
	docker compose exec redis redis-cli

# ── Code Quality ────────────────────────────────────────────────
lint:
	python -m ruff check backend/ tests/

format:
	python -m ruff format backend/ tests/

# ── Cleanup ─────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

# ── Quick Start ─────────────────────────────────────────────────
init: up
	@echo "Waiting for services to start..."
	@sleep 3
	$(MAKE) migrate
	@echo "Cortex is ready at http://localhost:8000"
