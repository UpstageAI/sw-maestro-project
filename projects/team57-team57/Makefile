.PHONY: install seed run smoke graph-diagram test lint format reset clean \
	docker-build docker-up docker-down docker-logs docker-seed docker-smoke

install:
	uv sync

seed:
	uv run python -m src.scripts.seed

run:
	uv run python -m streamlit run src/ui/app.py

smoke:
	uv run python -m src.scripts.smoke_test

graph-diagram:
	uv run python -m src.scripts.draw_graph

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/

reset:
	uv run python -m src.scripts.reset

clean:
	uv run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('.*_cache')]"

# --- Docker ----------------------------------------------------------------

docker-build:
	docker compose build

docker-up:
	docker compose up -d
	@echo "→ http://localhost:8501"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f app

docker-seed:
	docker compose exec app uv run python -m src.scripts.seed

docker-smoke:
	docker compose exec app uv run python -m src.scripts.smoke_test
