PYTHON := $(shell if command -v uv >/dev/null 2>&1; then echo "uv run python"; else echo "python3"; fi)
STREAMLIT := $(shell if command -v uv >/dev/null 2>&1; then echo "uv run streamlit"; else echo "python3 -m streamlit"; fi)
PYTEST := $(shell if command -v uv >/dev/null 2>&1; then echo "uv run pytest"; else echo "python3 -m pytest"; fi)

.PHONY: run init-db test lint

run:
	$(STREAMLIT) run app.py

init-db:
	$(PYTHON) -m src.db.schema

test:
	$(PYTEST)

lint:
	$(PYTHON) -m compileall app.py src tests
