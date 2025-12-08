# CI/CD and Makefile Setup

## Overview

This guide covers the complete CI/CD setup for Blueprint including:
- GitHub Actions workflows
- Homebrew tap and formula
- Makefile for common tasks
- Automated releases

---

## File: `Makefile`

**Purpose**: Common development and release tasks

**Location**: Project root

**Content**:
```makefile
.PHONY: help install dev test lint format clean build publish brew-formula

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
install:
	pip install .

dev:
	pip install -e ".[dev]"

# Testing and quality
test:
	pytest tests/ -v --cov=src/blueprint --cov-report=html --cov-report=term

lint:
	@echo "Running ruff..."
	ruff check src/ tests/
	@echo "Running mypy..."
	mypy src/blueprint

format:
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
build: clean
	@echo "Building distribution packages..."
	python -m build

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
run:
	@python -m blueprint

# Version bump helpers
bump-patch:
	@echo "Bumping patch version..."
	@python scripts/bump_version.py patch

bump-minor:
	@echo "Bumping minor version..."
	@python scripts/bump_version.py minor

bump-major:
	@echo "Bumping major version..."
	@python scripts/bump_version.py major

# Check everything before release
pre-release: clean format lint test build
	@echo "✓ Pre-release checks passed"
	@echo "Ready to release!"
```

---

## File: `.github/workflows/ci.yml`

**Purpose**: Run checks on PRs and pushes to main

**Location**: `.github/workflows/ci.yml`

**Content**:
```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    name: Test on ${{ matrix.os }} - Python ${{ matrix.python-version }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache pip packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/pyproject.toml') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Run linters
      run: |
        ruff check src/ tests/
        mypy src/blueprint

    - name: Run tests
      run: |
        pytest tests/ -v --cov=src/blueprint --cov-report=xml

    - name: Upload coverage to Codecov
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  build:
    name: Build distribution
    runs-on: ubuntu-latest
    needs: test

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build

    - name: Build package
      run: python -m build

    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: dist
        path: dist/

  security:
    name: Security scan
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Run Bandit security scan
      uses: tj-actions/bandit@v5.5
      with:
        targets: src/
        options: "-r"
```

---

## File: `.github/workflows/release.yml`

**Purpose**: Automated release on GitHub release creation

**Location**: `.github/workflows/release.yml`

**Content**:
```yaml
name: Release

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    name: Build and publish to PyPI
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*

    - name: Upload release assets
      uses: softprops/action-gh-release@v1
      with:
        files: dist/*

  update-homebrew:
    name: Update Homebrew formula
    runs-on: ubuntu-latest
    needs: build-and-publish

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Get version
      id: version
      run: |
        VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
        echo "version=$VERSION" >> $GITHUB_OUTPUT

    - name: Generate Homebrew formula
      run: |
        python scripts/generate_formula.py ${{ steps.version.outputs.version }}

    - name: Commit to homebrew-blueprint tap
      run: |
        git config --global user.name 'github-actions[bot]'
        git config --global user.email 'github-actions[bot]@users.noreply.github.com'

        # Clone homebrew tap repo
        git clone https://${{ secrets.HOMEBREW_TAP_TOKEN }}@github.com/rafiki270/homebrew-blueprint.git
        cd homebrew-blueprint

        # Copy formula
        cp ../Formula/blueprint.rb Formula/

        # Commit and push
        git add Formula/blueprint.rb
        git commit -m "Update blueprint to ${{ steps.version.outputs.version }}"
        git push
```

---

## File: `scripts/generate_formula.py`

**Purpose**: Generate Homebrew formula automatically

**Location**: `scripts/generate_formula.py`

**Content**:
```python
#!/usr/bin/env python3
"""Generate Homebrew formula for Blueprint"""

import hashlib
import sys
import tomllib
from pathlib import Path


def get_version():
    """Get version from pyproject.toml"""
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    return config["project"]["version"]


def get_sha256(version):
    """Calculate SHA256 of PyPI package"""
    import urllib.request

    url = f"https://files.pythonhosted.org/packages/source/b/blueprint-cli/blueprint-cli-{version}.tar.gz"

    print(f"Downloading {url}...")
    with urllib.request.urlopen(url) as response:
        data = response.read()

    return hashlib.sha256(data).hexdigest()


def generate_formula(version, sha256):
    """Generate Homebrew formula"""
    formula = f'''class Blueprint < Formula
  include Language::Python::Virtualenv

  desc "Multi-LLM Development Orchestrator"
  homepage "https://github.com/rafiki270/blueprint"
  url "https://files.pythonhosted.org/packages/source/b/blueprint-cli/blueprint-cli-{version}.tar.gz"
  sha256 "{sha256}"
  license "MIT"

  depends_on "python@3.11"

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.7.tar.gz"
    sha256 "ca9853ad459e787e2192211578cc907e7594e294c7ccc834310722b41b9ca6de"
  end

  resource "textual" do
    url "https://files.pythonhosted.org/packages/source/t/textual/textual-0.47.1.tar.gz"
    sha256 "4b82e317884bb1092f693f474c319ceb068b5a0b128b121f1aa53a2d48b4b80c"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "5cb5123b5cf9ee70584244246816e9114227e0b98ad9176eede6ad54bf5403fa"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"blueprint", "--version"
  end
end
'''
    return formula


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version = get_version()

    print(f"Generating formula for version {version}")

    # Get SHA256
    sha256 = get_sha256(version)

    # Generate formula
    formula = generate_formula(version, sha256)

    # Write to file
    formula_dir = Path("Formula")
    formula_dir.mkdir(exist_ok=True)

    formula_file = formula_dir / "blueprint.rb"
    formula_file.write_text(formula)

    print(f"✓ Formula written to {formula_file}")
    print("\nNext steps:")
    print("1. Review Formula/blueprint.rb")
    print("2. Test with: brew install --build-from-source Formula/blueprint.rb")
    print("3. Commit to homebrew-blueprint tap")


if __name__ == "__main__":
    main()
```

**Make executable**:
```bash
chmod +x scripts/generate_formula.py
```

---

## File: `scripts/bump_version.py`

**Purpose**: Bump version in pyproject.toml

**Location**: `scripts/bump_version.py`

**Content**:
```python
#!/usr/bin/env python3
"""Bump version in pyproject.toml"""

import re
import sys
from pathlib import Path


def get_current_version():
    """Get current version from pyproject.toml"""
    content = Path("pyproject.toml").read_text()
    match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return tuple(map(int, match.groups()))


def bump_version(bump_type):
    """Bump version based on type"""
    major, minor, patch = get_current_version()

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"


def update_version(new_version):
    """Update version in pyproject.toml"""
    content = Path("pyproject.toml").read_text()
    updated = re.sub(
        r'version = "\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content
    )
    Path("pyproject.toml").write_text(updated)


def main():
    """Main entry point"""
    if len(sys.argv) != 2 or sys.argv[1] not in ["major", "minor", "patch"]:
        print("Usage: bump_version.py [major|minor|patch]")
        sys.exit(1)

    bump_type = sys.argv[1]
    old_version = ".".join(map(str, get_current_version()))
    new_version = bump_version(bump_type)

    print(f"Bumping {bump_type} version: {old_version} → {new_version}")
    update_version(new_version)
    print(f"✓ Updated pyproject.toml")

    print("\nNext steps:")
    print(f"1. git add pyproject.toml")
    print(f'2. git commit -m "Bump version to {new_version}"')
    print(f"3. git tag v{new_version}")
    print(f"4. git push && git push --tags")


if __name__ == "__main__":
    main()
```

**Make executable**:
```bash
chmod +x scripts/bump_version.py
```

---

## Homebrew Tap Setup

### Create Homebrew Tap Repository

1. **Create new repository**: `homebrew-blueprint`
2. **Location**: `https://github.com/rafiki270/homebrew-blueprint`

### Repository Structure
```
homebrew-blueprint/
├── README.md
└── Formula/
    └── blueprint.rb
```

### README.md for Tap
```markdown
# Homebrew Blueprint

Homebrew tap for Blueprint CLI.

## Installation

```bash
brew tap rafiki270/blueprint
brew install blueprint
```

## Usage

```bash
blueprint --version
blueprint
```

## Documentation

See main repository: https://github.com/rafiki270/blueprint
```

---

## Release Workflow

### Step-by-Step Release Process

1. **Prepare Release**
   ```bash
   # Ensure you're on main branch
   git checkout main
   git pull

   # Run pre-release checks
   make pre-release
   ```

2. **Bump Version**
   ```bash
   # Choose appropriate bump
   make bump-patch   # 0.1.0 → 0.1.1
   # OR
   make bump-minor   # 0.1.0 → 0.2.0
   # OR
   make bump-major   # 0.1.0 → 1.0.0
   ```

3. **Update Changelog**
   ```bash
   # Edit CHANGELOG.md with new version changes
   vim CHANGELOG.md
   ```

4. **Commit and Tag**
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Release version X.Y.Z"
   git tag vX.Y.Z
   git push && git push --tags
   ```

5. **Create GitHub Release**
   - Go to GitHub repository
   - Click "Releases" → "Draft a new release"
   - Select tag: `vX.Y.Z`
   - Title: `Blueprint vX.Y.Z`
   - Description: Copy from CHANGELOG.md
   - Click "Publish release"

6. **Automated Actions** (triggered by release)
   - ✓ Run CI tests
   - ✓ Build packages
   - ✓ Publish to PyPI
   - ✓ Generate Homebrew formula
   - ✓ Update homebrew-blueprint tap

7. **Verify Release**
   ```bash
   # Test PyPI install
   pip install --upgrade blueprint-cli
   blueprint --version

   # Test Homebrew install (wait 5-10 min for tap update)
   brew upgrade blueprint
   blueprint --version
   ```

---

## GitHub Secrets Configuration

Required secrets in GitHub repository settings:

### `PYPI_API_TOKEN`
1. Go to https://pypi.org/manage/account/token/
2. Create new API token
3. Scope: Entire account or specific project
4. Copy token
5. Add to GitHub: Settings → Secrets → Actions → New repository secret
   - Name: `PYPI_API_TOKEN`
   - Value: `pypi-...`

### `HOMEBREW_TAP_TOKEN`
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Scopes: `repo` (full control)
4. Copy token
5. Add to GitHub: Settings → Secrets → Actions → New repository secret
   - Name: `HOMEBREW_TAP_TOKEN`
   - Value: `ghp_...`

---

## Development Workflow Examples

### Daily Development
```bash
# Setup
make dev

# Make changes...
vim src/blueprint/...

# Format and lint
make format
make lint

# Test
make test

# Run
make run
```

### Before Submitting PR
```bash
# Clean everything
make clean

# Run all checks
make pre-release

# Push
git push origin feature-branch
```

### Quick Test of Package
```bash
# Build
make build

# Install locally
pip install dist/*.whl

# Test
blueprint --version
```

---

## CI/CD Badge Setup

Add to `README.md`:

```markdown
![CI](https://github.com/rafiki270/blueprint/workflows/CI/badge.svg)
![Release](https://github.com/rafiki270/blueprint/workflows/Release/badge.svg)
[![PyPI version](https://badge.fury.io/py/blueprint-cli.svg)](https://badge.fury.io/py/blueprint-cli)
[![codecov](https://codecov.io/gh/rafiki270/blueprint/branch/main/graph/badge.svg)](https://codecov.io/gh/rafiki270/blueprint)
```

---

## Makefile Quick Reference

```bash
# Installation
make install          # Production install
make dev              # Development install

# Code Quality
make format           # Format code
make lint             # Run linters
make test             # Run tests

# Building
make clean            # Remove artifacts
make build            # Build packages

# Publishing
make publish-test     # Test PyPI
make publish          # Production PyPI

# Version Management
make bump-patch       # Bump patch version
make bump-minor       # Bump minor version
make bump-major       # Bump major version

# Homebrew
make brew-formula     # Generate formula

# Complete checks
make pre-release      # Run all checks
```

---

## Testing Checklist

### Before Release
- [ ] All tests pass: `make test`
- [ ] Linters pass: `make lint`
- [ ] Code formatted: `make format`
- [ ] Build succeeds: `make build`
- [ ] Version bumped correctly
- [ ] CHANGELOG.md updated
- [ ] Documentation updated

### After Release
- [ ] PyPI package available
- [ ] PyPI install works: `pip install blueprint-cli`
- [ ] Homebrew formula updated
- [ ] Homebrew install works: `brew install rafiki270/blueprint/blueprint`
- [ ] GitHub release created
- [ ] All CI checks passed
- [ ] Badges updated

---

## Troubleshooting

### PyPI Upload Fails
```bash
# Check credentials
twine check dist/*

# Verify token
# Update PYPI_API_TOKEN secret
```

### Homebrew Formula Issues
```bash
# Test formula locally
brew install --build-from-source Formula/blueprint.rb

# Audit formula
brew audit --strict Formula/blueprint.rb

# Test installation
brew test blueprint
```

### CI Failing
```bash
# Run same checks locally
make pre-release

# Check specific workflow
cat .github/workflows/ci.yml

# View logs on GitHub
# Go to Actions tab → Select failed run
```

---

This complete CI/CD setup ensures Blueprint can be:
- ✅ Tested automatically on every push
- ✅ Released to PyPI automatically
- ✅ Distributed via Homebrew
- ✅ Managed easily with Makefile commands
