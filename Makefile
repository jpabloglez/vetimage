# OpenMedLab Project Makefile
# Comprehensive Docker management commands

.PHONY: help build up down restart logs shell-backend shell-frontend shell-db exec-backend exec-frontend exec-db clean prune status ps commit push pull dev prod backup restore test lint check health migrate seed reset install update services-up services-down services-ps services-logs services-restart mirage-up mirage-down mirage-logs mirage-shell mirage-restart mirage-refresh chexnet-up chexnet-down chexnet-logs chexnet-shell chexnet-restart chexnet-refresh picai-up picai-down picai-logs picai-shell picai-restart picai-refresh picai-health fastsurfer-up fastsurfer-down fastsurfer-logs fastsurfer-shell fastsurfer-restart fastsurfer-refresh fastsurfer-health models-seed models-list models-health

# Default target
help: ## Show this help message
	@echo "OpenMedLab Project - Docker Management Commands"
	@echo "=================================================="
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

# Build Commands
build: ## Build all services
	docker-compose build

build-backend: ## Build only backend service
	docker-compose build backend-openmedlab

build-frontend: ## Build only frontend service
	docker-compose build frontend-openmedlab

build-gateway: ## Build DICOM gateway service
	docker-compose build dicom-gateway-openmedlab gateway-celery-worker

build-db: ## Build database service
	docker-compose build db-openmedlab

build-orthanc: ## Build Orthanc test PACS
	docker-compose build orthanc-test-pacs

build-redis: ## Build Redis service
	docker-compose build redis-openmedlab

build-orchestrator: ## Build orchestrator service
	docker-compose build orchestrator-openmedlab

build-no-cache: ## Build all services without cache
	docker-compose build --no-cache

# Service Management
up: ## Start all services in detached mode
	docker-compose up -d

up-logs: ## Start all services and show logs
	docker-compose up

up-detached: ## Start all services in detached mode
	docker-compose up -d

up-backend: ## Start backend service
	docker-compose up -d backend-openmedlab

up-frontend: ## Start frontend service
	docker-compose up -d frontend-openmedlab

up-db: ## Start database service
	docker-compose up -d db-openmedlab

up-gateway: ## Start DICOM gateway service
	docker-compose up -d dicom-gateway-openmedlab gateway-celery-worker

up-orthanc: ## Start Orthanc test PACS
	docker-compose up -d orthanc-test-pacs

up-redis: ## Start Redis service
	docker-compose up -d redis-openmedlab

up-orchestrator: ## Start orchestrator service
	docker-compose up -d orchestrator-openmedlab

up-services: ## Start all AI model services
	docker compose -f docker-compose.yml -f docker-compose.services.yml up -d mirage-service chexnet-service picai-service

up-services-picai: ## Start PicAI service
	docker compose -f docker-compose.yml -f docker-compose.services.yml up -d orchestrator-openmedlab picai-service

down: ## Stop and remove all containers
	docker-compose down

down-volumes: ## Stop containers and remove volumes
	docker-compose down -v

restart: ## Restart all services
	docker-compose restart

restart-backend: ## Restart backend service
	docker-compose restart backend-openmedlab

restart-frontend: ## Restart frontend service
	docker-compose restart frontend-openmedlab

restart-db: ## Restart database service
	docker-compose restart db-openmedlab

restart-gateway: ## Restart DICOM gateway service
	docker-compose restart dicom-gateway-openmedlab

restart-orthanc: ## Restart Orthanc test PACS
	docker-compose restart orthanc-test-pacs

restart-gateway-worker: ## Restart gateway Celery worker
	docker-compose restart gateway-celery-worker

# Development Commands
dev: ## Start development environment
	docker-compose up -d && make logs

prod: build ## Build and start production environment
	docker-compose up -d

# Logging
logs: ## Show logs for all services
	docker-compose logs -f

logs-backend: ## Show logs for backend service
	docker-compose logs -f backend-openmedlab --timestamps

logs-frontend: ## Show logs for frontend service
	docker-compose logs -f frontend-openmedlab

logs-db: ## Show logs for database service
	docker-compose logs -f db-openmedlab

logs-gateway: ## Show logs for DICOM gateway service
	docker-compose logs -f dicom-gateway-openmedlab

logs-gateway-worker: ## Show logs for gateway Celery worker
	docker-compose logs -f gateway-celery-worker

logs-orthanc: ## Show logs for Orthanc test PACS
	docker-compose logs -f orthanc-test-pacs
	
logs-redis: ## Show logs for Redis service
	docker-compose logs -f redis-openmedlab

logs-orchestrator: ## Show logs for orchestrator service
	docker-compose logs -f orchestrator-openmedlab

# Shell Access
shell-backend: ## Access backend container shell
	docker-compose exec backend-openmedlab bash

shell-frontend: ## Access frontend container shell
	docker-compose exec frontend-openmedlab bash

shell-db: ## Access database container shell
	docker-compose exec db-openmedlab psql -U postgres -d postgres

shell-gateway: ## Access DICOM gateway container shell
	docker-compose exec dicom-gateway-openmedlab bash

shell-orthanc: ## Access Orthanc container shell
	docker-compose exec orthanc-test-pacs bash

# Execute Commands
exec-backend: ## Execute command in backend container (use CMD="your command")
	docker-compose exec backend-openmedlab $(CMD)

exec-frontend: ## Execute command in frontend container (use CMD="your command")
	docker-compose exec frontend-openmedlab $(CMD)

exec-db: ## Execute SQL command in database (use CMD="your query")
	docker-compose exec db-openmedlab psql -U postgres -d postgres -c "$(CMD)"

# Status and Information
status: ## Show container status
	docker-compose ps

ps: status ## Alias for status

health: ## Check health of all services
	docker-compose ps
	@echo ""
	@echo "Backend health:"
	@curl -f http://localhost:3080/health 2>/dev/null || echo "Backend not responding"
	@echo ""
	@echo "Frontend health:"
	@curl -f http://localhost:3000 2>/dev/null > /dev/null && echo "Frontend responding" || echo "Frontend not responding"
	@echo ""
	@echo "DICOM Gateway health:"
	@curl -f http://localhost:8001/health 2>/dev/null || echo "Gateway not responding"
	@echo ""
	@echo "Orthanc health:"
	@curl -f http://localhost:8042/system 2>/dev/null > /dev/null && echo "Orthanc responding" || echo "Orthanc not responding"

# Database Operations
migrate: ## Run database migrations
	docker-compose exec backend-openmedlab python manage.py migrate

makemigrations: ## Create new migrations
	docker-compose exec backend-openmedlab python manage.py makemigrations

seed: ## Seed database with initial data
	docker-compose exec backend-openmedlab python manage.py loaddata fixtures/initial_data.json

backup: ## Backup database to ./backups/
	@mkdir -p backups
	docker-compose exec db-openmedlab pg_dump -U postgres postgres > backups/backup-$$(date +%Y%m%d_%H%M%S).sql

restore: ## Restore database from backup (use FILE="backup_file.sql")
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backup_file.sql"; exit 1; fi
	docker-compose exec -T db-openmedlab psql -U postgres -d postgres < $(FILE)

# Installation and Dependencies
install: ## Install dependencies in containers
	docker-compose exec backend-openmedlab pip install -r requirements.txt
	docker-compose exec frontend-openmedlab npm install

install-backend: ## Install backend dependencies
	docker-compose exec backend-openmedlab pip install -r requirements.txt

install-frontend: ## Install frontend dependencies
	docker-compose exec frontend-openmedlab npm install

update: ## Update dependencies
	docker-compose exec backend-openmedlab pip install -r requirements.txt --upgrade
	docker-compose exec frontend-openmedlab npm update

# Testing
test: ## Run all tests
	docker-compose exec backend-openmedlab python manage.py test
	docker-compose exec frontend-openmedlab npm test

test-backend: ## Run backend tests
	docker-compose exec backend-openmedlab python manage.py test

test-frontend: ## Run frontend tests
	docker-compose exec frontend-openmedlab npm test

test-coverage: ## Run tests with coverage
	docker-compose exec backend-openmedlab coverage run --source='.' manage.py test
	docker-compose exec backend-openmedlab coverage report

# Linting and Code Quality
lint: ## Run linters for all services
	docker-compose exec backend-openmedlab flake8 .
	docker-compose exec frontend-openmedlab npm run lint

lint-backend: ## Run backend linting
	docker-compose exec backend-openmedlab flake8 .

lint-frontend: ## Run frontend linting
	docker-compose exec frontend-openmedlab npm run lint

format: ## Format code
	docker-compose exec backend-openmedlab black .
	docker-compose exec frontend-openmedlab npm run format

check: lint test ## Run all checks (lint + test)

# Git Operations
commit: ## Add all changes and commit (use MSG="commit message")
	@if [ -z "$(MSG)" ]; then echo "Usage: make commit MSG=\"your message\""; exit 1; fi
	git add .
	git commit -m "$(MSG)"

push: ## Push to remote repository
	git push origin $$(git branch --show-current)

pull: ## Pull from remote repository
	git pull origin $$(git branch --show-current)

# Cleanup
clean: ## Remove stopped containers and unused images
	docker-compose down
	docker system prune -f

clean-all: ## Remove all containers, images, and volumes
	docker-compose down -v --remove-orphans
	docker system prune -af

prune: clean ## Alias for clean

reset: clean-all build up ## Complete reset: clean everything, rebuild, and start

# Volume Management
volume-backup: ## Backup shared volume
	@mkdir -p backups
	docker run --rm -v openmedlab_shared_volume:/data -v $$(pwd)/backups:/backup alpine tar czf /backup/shared-volume-$$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

volume-restore: ## Restore shared volume (use FILE="backup.tar.gz")
	@if [ -z "$(FILE)" ]; then echo "Usage: make volume-restore FILE=backup.tar.gz"; exit 1; fi
	docker run --rm -v openmedlab_shared_volume:/data -v $$(pwd)/backups:/backup alpine tar xzf /backup/$(FILE) -C /data

# Monitoring
monitor: ## Monitor resource usage
	docker stats $$(docker-compose ps -q)

top: ## Show running processes in containers
	docker-compose top

# Network
network-ls: ## List networks
	docker network ls

network-inspect: ## Inspect app network
	docker network inspect openmedlab_app-network

# DICOM Gateway Commands
gateway-status: ## Show DICOM gateway status
	@curl -s http://localhost:8001/api/status | python -m json.tool

gateway-stats: ## Show DICOM gateway statistics
	@curl -s http://localhost:8001/api/stats | python -m json.tool

gateway-metrics: ## Show DICOM gateway system metrics
	@curl -s http://localhost:8001/api/metrics | python -m json.tool

gateway-test-echo: ## Test DICOM gateway C-ECHO connectivity
	@curl -X POST http://localhost:8001/api/test-echo

gateway-logs-live: ## Show live gateway logs
	docker-compose logs -f --tail=100 dicom-gateway-openmedlab

# Orthanc Commands
orthanc-open: ## Open Orthanc web interface in browser
	@echo "Opening Orthanc at http://localhost:8042"
	@echo "Username: orthanc"
	@echo "Password: orthanc"
	@python -m webbrowser http://localhost:8042 2>/dev/null || open http://localhost:8042 2>/dev/null || xdg-open http://localhost:8042 2>/dev/null || echo "Please open http://localhost:8042 in your browser"

orthanc-status: ## Check Orthanc system status
	@curl -s http://localhost:8042/system -u orthanc:orthanc | python -m json.tool

orthanc-modalities: ## List configured DICOM modalities
	@curl -s http://localhost:8042/modalities -u orthanc:orthanc | python -m json.tool

orthanc-echo-gateway: ## Test C-ECHO from Orthanc to Gateway
	@echo "Testing DICOM connectivity from Orthanc to Gateway..."
	@curl -X POST http://localhost:8042/modalities/OPENMEDLAB/echo -u orthanc:orthanc && echo "✓ C-ECHO successful"

orthanc-studies: ## List studies in Orthanc
	@curl -s http://localhost:8042/studies -u orthanc:orthanc | python -m json.tool

orthanc-send-study: ## Send study from Orthanc to Gateway (use STUDY_ID=xxx)
	@if [ -z "$(STUDY_ID)" ]; then echo "Usage: make orthanc-send-study STUDY_ID=study-uuid"; exit 1; fi
	@echo "Sending study $(STUDY_ID) to Gateway..."
	@curl -X POST http://localhost:8042/modalities/OPENMEDLAB/store -u orthanc:orthanc -d '{"Resources":["$(STUDY_ID)"],"Synchronous":false}' | python -m json.tool

# =============================================================================
# AI Model Services (docker-compose.services.yml)
# =============================================================================

SERVICES_COMPOSE = -f docker-compose.yml -f docker-compose.services.yml

# --- All services -----------------------------------------------------------

services-up: ## Start all AI model services
	docker compose $(SERVICES_COMPOSE) up -d mirage-service chexnet-service picai-service fastsurfer-service

services-down: ## Stop all AI model services
	docker compose $(SERVICES_COMPOSE) stop mirage-service chexnet-service picai-service fastsurfer-service
	docker compose $(SERVICES_COMPOSE) rm -f mirage-service chexnet-service picai-service fastsurfer-service

services-ps: ## Show status of AI model services
	docker compose $(SERVICES_COMPOSE) ps mirage-service chexnet-service picai-service fastsurfer-service

services-logs: ## Show logs from all AI model services
	docker compose $(SERVICES_COMPOSE) logs -f mirage-service chexnet-service picai-service fastsurfer-service

services-restart: ## Restart all AI model services
	docker compose $(SERVICES_COMPOSE) restart mirage-service chexnet-service picai-service fastsurfer-service

# --- MIRAGE (OCT, port 8010) ------------------------------------------------

mirage-up: ## Start MIRAGE service
	docker compose $(SERVICES_COMPOSE) up -d mirage-service

mirage-down: ## Stop MIRAGE service
	docker compose $(SERVICES_COMPOSE) stop mirage-service

mirage-logs: ## Show MIRAGE service logs
	docker compose $(SERVICES_COMPOSE) logs -f mirage-service

mirage-shell: ## Open shell in MIRAGE container
	docker compose $(SERVICES_COMPOSE) exec mirage-service bash

mirage-restart: ## Restart MIRAGE service
	docker compose $(SERVICES_COMPOSE) restart mirage-service

mirage-refresh: ## Force-recreate MIRAGE container (picks up config changes)
	docker compose $(SERVICES_COMPOSE) up -d --force-recreate mirage-service

mirage-health: ## Check MIRAGE service health
	@curl -sf http://localhost:8010/health | python3 -m json.tool || echo "MIRAGE service not responding"

mirage-load-base: ## Pre-load MIRAGE base model into GPU
	@curl -sf -X POST http://localhost:8010/models/base/load | python3 -m json.tool

mirage-load-large: ## Pre-load MIRAGE large model into GPU
	@curl -sf -X POST http://localhost:8010/models/large/load | python3 -m json.tool

mirage-register: ## Register MIRAGE model in the database
	docker compose exec backend-openmedlab python manage.py register_mirage --url http://mirage-service:8000 --update

# --- CheXNet (Chest X-ray, port 8011) ---------------------------------------

chexnet-up: ## Start CheXNet service
	docker compose $(SERVICES_COMPOSE) up -d chexnet-service

chexnet-down: ## Stop CheXNet service
	docker compose $(SERVICES_COMPOSE) stop chexnet-service

chexnet-logs: ## Show CheXNet service logs
	docker compose $(SERVICES_COMPOSE) logs -f chexnet-service

chexnet-shell: ## Open shell in CheXNet container
	docker compose $(SERVICES_COMPOSE) exec chexnet-service bash

chexnet-restart: ## Restart CheXNet service
	docker compose $(SERVICES_COMPOSE) restart chexnet-service

chexnet-refresh: ## Force-recreate CheXNet container (picks up config changes)
	docker compose $(SERVICES_COMPOSE) up -d --force-recreate chexnet-service

chexnet-health: ## Check CheXNet service health
	@curl -sf http://localhost:8011/health | python3 -m json.tool || echo "CheXNet service not responding"

# --- PICAI (Prostate MRI, port 50051, requires orchestrator) -----------------

picai-up: ## Start PICAI service + orchestrator
	docker compose $(SERVICES_COMPOSE) up -d orchestrator-openmedlab picai-service

picai-down: ## Stop PICAI service
	docker compose $(SERVICES_COMPOSE) stop picai-service

picai-logs: ## Show PICAI service logs
	docker compose $(SERVICES_COMPOSE) logs -f picai-service

picai-shell: ## Open shell in PICAI container
	docker compose $(SERVICES_COMPOSE) exec picai-service bash

picai-restart: ## Restart PICAI service
	docker compose $(SERVICES_COMPOSE) restart picai-service

picai-refresh: ## Force-recreate PICAI container (picks up config changes)
	docker compose $(SERVICES_COMPOSE) up -d --force-recreate picai-service

picai-health: ## Check PICAI gRPC health
	@python3 -c "import grpc; ch=grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(ch).result(timeout=5); print('PICAI gRPC: healthy')" 2>/dev/null || echo "PICAI service not responding"

# --- FastSurfer (Brain MRI, gRPC port 50052, REST port 8012) ----------------

fastsurfer-up: ## Start FastSurfer service + orchestrator
	docker compose $(SERVICES_COMPOSE) up -d orchestrator-openmedlab fastsurfer-service

fastsurfer-down: ## Stop FastSurfer service
	docker compose $(SERVICES_COMPOSE) stop fastsurfer-service

fastsurfer-logs: ## Show FastSurfer service logs
	docker compose $(SERVICES_COMPOSE) logs -f fastsurfer-service

fastsurfer-shell: ## Open shell in FastSurfer container
	docker compose $(SERVICES_COMPOSE) exec fastsurfer-service bash

fastsurfer-restart: ## Restart FastSurfer service
	docker compose $(SERVICES_COMPOSE) restart fastsurfer-service

fastsurfer-refresh: ## Force-recreate FastSurfer container (picks up config changes)
	docker compose $(SERVICES_COMPOSE) up -d --force-recreate fastsurfer-service

fastsurfer-health: ## Check FastSurfer REST health
	@curl -sf http://localhost:8012/health | python3 -m json.tool || echo "FastSurfer service not responding"

# --- Model registration & diagnostics ---------------------------------------

models-seed: ## Register all AI models in the database
	docker compose exec backend-openmedlab python manage.py seed_ai_models

models-list: ## List registered AI models
	docker compose exec backend-openmedlab python manage.py shell -c \
		"from ai_analysis.models import AIModel; [print(f'{m.key:15} {m.name:20} active={m.is_active}  {m.endpoint_url}') for m in AIModel.objects.all()]"

models-health: ## Check health of all running model services
	@echo "=== MIRAGE (localhost:8010) ==="
	@curl -sf http://localhost:8010/health 2>/dev/null | python3 -m json.tool || echo "  Not running"
	@echo ""
	@echo "=== CheXNet (localhost:8011) ==="
	@curl -sf http://localhost:8011/health 2>/dev/null | python3 -m json.tool || echo "  Not running"
	@echo ""
	@echo "=== FastSurfer REST (localhost:8012) ==="
	@curl -sf http://localhost:8012/health 2>/dev/null | python3 -m json.tool || echo "  Not running"
	@echo ""
	@echo "=== Orchestrator (localhost:8080) ==="
	@curl -sf http://localhost:8080/health 2>/dev/null | python3 -m json.tool || echo "  Not running"
