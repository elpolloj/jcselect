# Makefile for jcselect project

.PHONY: help test translations validate-translations clean install run

help:
	@echo "Available commands:"
	@echo "  install              Install dependencies"
	@echo "  test                 Run all tests"
	@echo "  translations         Generate .qm files from .ts files"
	@echo "  validate-translations   Validate translation loading"
	@echo "  run                  Run the application"
	@echo "  clean                Clean generated files"

install:
	poetry install

test:
	poetry run pytest -q

translations:
	poetry run python scripts/generate_translations.py

validate-translations:
	poetry run python scripts/validate_translations.py

run:
	poetry run python -m jcselect

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -f src/jcselect/i18n/*.qm

# Pre-commit target to run translations and tests
pre-commit: translations test validate-translations
	@echo "✅ Pre-commit checks passed!" 