.PHONY: help dev prod shell migrate makemigrations superuser test clean logs backup restore

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start development environment
	docker compose -f docker-compose.dev.yml up --build

dev-down: ## Stop development environment
	docker compose -f docker-compose.dev.yml down

prod: ## Start production environment
	docker compose -f docker-compose.prod.yml up -d --build

prod-down: ## Stop production environment
	docker compose -f docker-compose.prod.yml down

shell: ## Open Django shell in development
	docker compose -f docker-compose.dev.yml exec web python manage.py shell

shell-prod: ## Open Django shell in production
	docker compose -f docker-compose.prod.yml exec web python manage.py shell

migrate: ## Run migrations in development
	docker compose -f docker-compose.dev.yml exec web python manage.py migrate

migrate-prod: ## Run migrations in production
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate

makemigrations: ## Create new migrations in development
	docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations

superuser: ## Create superuser in development
	docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser

superuser-prod: ## Create superuser in production
	docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

test: ## Run tests in development
	docker compose -f docker-compose.dev.yml exec web pytest

logs: ## Show logs for development
	docker compose -f docker-compose.dev.yml logs -f

logs-prod: ## Show logs for production
	docker compose -f docker-compose.prod.yml logs -f

clean: ## Clean up Docker volumes and containers
	docker compose -f docker-compose.dev.yml down -v
	docker compose -f docker-compose.prod.yml down -v
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

backup: ## Backup production database
	./scripts/backup_db.sh

restore: ## Restore production database from backup
	@echo "Usage: make restore BACKUP_FILE=backups/backup_YYYYMMDD_HHMMSS.sql"
	@test -n "$(BACKUP_FILE)" || (echo "Error: BACKUP_FILE is required" && exit 1)
	./scripts/restore_db.sh $(BACKUP_FILE)

collectstatic: ## Collect static files in development
	docker compose -f docker-compose.dev.yml exec web python manage.py collectstatic --noinput

collectstatic-prod: ## Collect static files in production
	docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput