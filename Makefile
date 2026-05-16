ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
DEV_COMPOSE  := podman compose -f $(ROOT_DIR)infra/compose/docker-compose.dev.yml
PROD_COMPOSE := podman compose -f $(ROOT_DIR)infra/compose/docker-compose.prod.yml

.PHONY: help \
        dev-up dev-down dev-status dev-build dev-logs \
        prod-up prod-down prod-status prod-logs prod-build \
        test migrate seed

help:
	@echo "Development"
	@echo "  make dev-up       Start db + backend + frontend (all in Docker)"
	@echo "  make dev-down     Stop dev containers"
	@echo "  make dev-status   Show dev container status"
	@echo "  make dev-build    Rebuild dev images"
	@echo "  make dev-logs     Follow dev logs"
	@echo ""
	@echo "Production"
	@echo "  make prod-up      Start all services (db, backend, frontend, caddy)"
	@echo "  make prod-down    Stop prod containers"
	@echo "  make prod-status  Show prod container status"
	@echo "  make prod-logs    Follow prod logs"
	@echo "  make prod-build   Rebuild prod images"
	@echo ""
	@echo "Backend"
	@echo "  make test         Run backend test suite"
	@echo "  make migrate      Run alembic upgrade head inside dev backend"
	@echo "  make seed         Seed db with sample items and price history"

# ── Development ──────────────────────────────────────────────────────────────

dev-up:
	$(DEV_COMPOSE) up -d
	@printf '\n%s\n' 'Dev services:'
	@printf '%s\n' '  frontend:  http://localhost:5173'
	@printf '%s\n' '  backend:   http://localhost:8000'
	@printf '%s\n' '  api docs:  http://localhost:8000/docs'
	@printf '%s\n' '  admin:     http://localhost:8000/admin'

dev-down:
	$(DEV_COMPOSE) down

dev-status:
	$(DEV_COMPOSE) ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"

dev-build:
	$(DEV_COMPOSE) build

dev-logs:
	$(DEV_COMPOSE) logs -f

# ── Production ───────────────────────────────────────────────────────────────

prod-up:
	$(PROD_COMPOSE) up -d

prod-down:
	$(PROD_COMPOSE) down

prod-status:
	$(PROD_COMPOSE) ps --format "table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"

prod-logs:
	$(PROD_COMPOSE) logs -f

prod-build:
	$(PROD_COMPOSE) build

# ── Backend helpers ───────────────────────────────────────────────────────────

test:
	cd $(ROOT_DIR)backend && \
	  $(DEV_COMPOSE) up db -d && \
	  podman exec $$(podman ps -q --filter name=db) psql -U postgres -c "CREATE DATABASE app_test;" 2>/dev/null || true && \
	  uv run pytest

migrate:
	$(DEV_COMPOSE) exec backend uv run alembic upgrade head

seed:
	$(DEV_COMPOSE) exec backend uv run python seed.py
