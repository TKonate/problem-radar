# Problem Radar — development shortcuts.
#
#   make install     create .venv and install with dev tools
#   make collect     collect signals with the committed configuration
#   make report      cluster, score and write the report
#   make run         collect + cluster + report
#   make test        run the test suite
#   make lint        ruff
#   make typecheck   mypy
#   make coverage    tests with a coverage report
#   make check       lint + typecheck + tests (what CI runs)
#   make clean       remove caches and build artefacts

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: install collect report run test lint typecheck coverage check clean

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"

collect:
	$(BIN)/python -m problem_radar collect

report:
	$(BIN)/python -m problem_radar cluster
	$(BIN)/python -m problem_radar report

run:
	$(BIN)/python -m problem_radar run

test:
	$(BIN)/python -m pytest -q

lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck:
	$(BIN)/mypy

coverage:
	$(BIN)/python -m pytest -q --cov=problem_radar --cov-report=term-missing

check: lint typecheck test

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov build dist *.egg-info
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
