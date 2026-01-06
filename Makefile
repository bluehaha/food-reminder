.PHONY: help install test lint format check clean run

help:
	@echo "Available commands:"
	@echo "  install  - Install dependencies with Poetry"
	@echo "  test     - Run tests with coverage"
	@echo "  lint     - Run linters (ruff, mypy)"
	@echo "  format   - Format code with black"
	@echo "  check    - Run all checks (format, lint, test)"
	@echo "  clean    - Clean generated files"
	@echo "  run      - Run the checker"

install:
	poetry install

test:
	poetry run pytest

lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run black src tests scripts

check: format lint test

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache

run:
	poetry run python scripts/check_availability.py
