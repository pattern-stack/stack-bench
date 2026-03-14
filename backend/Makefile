.PHONY: dev test ci lint format typecheck migrate seed

dev:
	uvicorn organisms.api.app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest

ci: format lint typecheck test

format:
	ruff format .

lint:
	ruff check . --fix

typecheck:
	mypy .

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

seed:
	@echo "No seed data yet"
