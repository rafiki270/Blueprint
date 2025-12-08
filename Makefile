.PHONY: help install dev test lint format clean build publish publish-test brew-formula run bump-patch bump-minor bump-major pre-release python-check

# Try to auto-detect a usable Python; override with `make PYTHON=/path/to/python`
PYTHON ?= $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null || echo python3)
MIN_PYTHON ?= 3.9

# Default target
help:
	@echo "Blueprint Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install Blueprint in production mode"
	@echo "  dev            Install in development mode with dev dependencies"
	@echo "  test           Run test suite"
	@echo "  lint           Run linters (ruff, mypy)"
	@echo "  format         Format code with black"
	@echo "  clean          Remove build artifacts and cache"
	@echo "  build          Build distribution packages"
	@echo "  publish        Publish to PyPI (requires credentials)"
	@echo "  publish-test   Publish to Test PyPI"
	@echo "  brew-formula   Generate Homebrew formula"
	@echo "  run            Run Blueprint in interactive mode"

# Installation targets
install: python-check
	$(PYTHON) -m pip install .
	$(PYTHON) -m pip install click

dev: python-check
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install click

# Testing and quality
test: python-check
	pytest tests/ -v --cov=src/blueprint --cov-report=html --cov-report=term

lint: python-check
	@echo "Running ruff..."
	ruff check src/ tests/
	@echo "Running mypy..."
	mypy src/blueprint

format: python-check
	@echo "Formatting with black..."
	black src/ tests/
	@echo "Sorting imports..."
	ruff check --select I --fix src/ tests/

# Cleaning
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	@echo "Cleaning Python cache..."
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

# Building
build: python-check clean
	@echo "Building distribution packages..."
	$(PYTHON) -m build

# Publishing
publish: build
	@echo "Publishing to PyPI..."
	twine upload dist/*

publish-test: build
	@echo "Publishing to Test PyPI..."
	twine upload --repository testpypi dist/*

# Homebrew formula generation
brew-formula:
	@echo "Generating Homebrew formula..."
	@python scripts/generate_formula.py

# Development
run: python-check
	@$(PYTHON) -m blueprint

# Version bump helpers
bump-patch:
	@echo "Bumping patch version..."
	@$(PYTHON) scripts/bump_version.py patch

bump-minor:
	@echo "Bumping minor version..."
	@$(PYTHON) scripts/bump_version.py minor

bump-major:
	@echo "Bumping major version..."
	@$(PYTHON) scripts/bump_version.py major

# Check everything before release
pre-release: python-check clean format lint test build
	@echo "✓ Pre-release checks passed"
	@echo "Ready to release!"

python-check:
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "Error: $(PYTHON) not found. Set PYTHON=/path/to/python"; exit 1; }
	@$(PYTHON) -c "import sys; min_req=tuple(map(int,'$(MIN_PYTHON)'.split('.'))); cur=sys.version_info[:2]; \
	  sys.exit(f'Python {min_req[0]}.{min_req[1]}+ required, found {cur[0]}.{cur[1]}') if cur < min_req else None"
