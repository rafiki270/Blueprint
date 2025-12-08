# Phase 8: Packaging & Distribution

## Overview
This phase packages Blueprint for distribution via PyPI and ensures cross-platform compatibility.

## Dependencies
- All previous phases should be complete
- Python packaging tools installed

## Files to Create

```
├── pyproject.toml
├── setup.py
├── setup.cfg
├── MANIFEST.in
├── .gitignore (update)
└── requirements.txt
```

## File: `pyproject.toml`
**Purpose**: Modern Python packaging configuration

**Content**:
```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "blueprint-cli"
version = "0.1.0"
description = "Multi-LLM Development Orchestrator"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Blueprint Contributors", email = "blueprint@example.com"}
]
keywords = ["llm", "orchestrator", "cli", "development", "automation"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
    "Environment :: Console",
    "Topic :: Software Development",
    "Topic :: Software Development :: Code Generators",
]

dependencies = [
    "click>=8.0",
    "textual>=0.47.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "black>=23.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
]

[project.urls]
Homepage = "https://github.com/your-org/blueprint"
Documentation = "https://github.com/your-org/blueprint/tree/main/Docs"
Repository = "https://github.com/your-org/blueprint"
"Bug Tracker" = "https://github.com/your-org/blueprint/issues"

[project.scripts]
blueprint = "blueprint.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
include = ["blueprint*"]

[tool.setuptools.package-data]
blueprint = ["py.typed"]

[tool.black]
line-length = 100
target-version = ["py310"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py310"
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
```

## File: `setup.py`
**Purpose**: Backward compatibility setup script

**Content**:
```python
#!/usr/bin/env python
"""Setup script for Blueprint"""

from setuptools import setup

# Configuration is in pyproject.toml
# This file exists for backward compatibility

if __name__ == "__main__":
    setup()
```

## File: `setup.cfg`
**Purpose**: Additional configuration

**Content**:
```ini
[metadata]
description_file = README.md
long_description_content_type = text/markdown

[options]
zip_safe = False
include_package_data = True

[options.package_data]
* = py.typed

[bdist_wheel]
universal = 0

[flake8]
max-line-length = 100
extend-ignore = E203, E501
exclude =
    .git,
    __pycache__,
    build,
    dist,
    .eggs,
    *.egg-info
```

## File: `MANIFEST.in`
**Purpose**: Include non-Python files in distribution

**Content**:
```
include README.md
include LICENSE
include requirements.txt
recursive-include src/blueprint *.py
recursive-include Docs *.md
recursive-exclude * __pycache__
recursive-exclude * *.py[co]
```

## File: `requirements.txt`
**Purpose**: Pin dependencies for reproducibility

**Content**:
```
click>=8.0,<9.0
textual>=0.47.0,<1.0
rich>=13.0.0,<14.0
```

## File: `.gitignore` (Update)
**Purpose**: Exclude build artifacts and virtual environments

**Content**:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/

# Blueprint state (for development)
.blueprint/

# OS
.DS_Store
Thumbs.db
```

## Building the Package

### Local Development Install

```bash
# Install in editable mode
pip install -e .

# With dev dependencies
pip install -e ".[dev]"
```

### Building for Distribution

```bash
# Install build tools
pip install build twine

# Build distribution
python -m build

# This creates:
# dist/blueprint_cli-0.1.0-py3-none-any.whl
# dist/blueprint-cli-0.1.0.tar.gz
```

### Testing the Build

```bash
# Install from local wheel
pip install dist/blueprint_cli-0.1.0-py3-none-any.whl

# Test it works
blueprint --version
```

### Publishing to PyPI

```bash
# Test PyPI (recommended first)
twine upload --repository testpypi dist/*

# Install from test PyPI
pip install --index-url https://test.pypi.org/simple/ blueprint-cli

# Production PyPI
twine upload dist/*
```

## Cross-Platform Testing

### macOS
```bash
# Should work out of the box
pip install blueprint-cli
blueprint --version
```

### Linux
```bash
# Debian/Ubuntu
sudo apt-get install python3-pip
pip3 install blueprint-cli
blueprint --version

# Fedora/RHEL
sudo dnf install python3-pip
pip3 install blueprint-cli
blueprint --version
```

### Windows (WSL)
```bash
# In WSL2
pip install blueprint-cli
blueprint --version
```

## Version Management

### Version Bumping Strategy

Update version in `pyproject.toml`:
```toml
version = "0.2.0"  # Semantic versioning
```

Version scheme:
- **0.1.0** - Initial alpha release
- **0.2.0** - Add new features
- **0.2.1** - Bug fixes
- **1.0.0** - First stable release

### Git Tagging

```bash
# Create version tag
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

## GitHub Release Workflow

### Create Release Workflow (`.github/workflows/release.yml`)

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

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
```

## Testing Checklist
- [ ] Package builds without errors
- [ ] Wheel file is created correctly
- [ ] Source distribution includes all files
- [ ] Entry point works after install
- [ ] Installation works on macOS
- [ ] Installation works on Linux (Ubuntu, Fedora)
- [ ] Installation works in WSL
- [ ] Package can be uploaded to test PyPI
- [ ] Installation from PyPI works
- [ ] All dependencies are correctly specified
- [ ] README renders correctly on PyPI

## Distribution Checklist

Pre-release:
- [ ] Update version in pyproject.toml
- [ ] Update CHANGELOG.md
- [ ] Run all tests
- [ ] Build package locally
- [ ] Test installation from wheel
- [ ] Test all CLI commands
- [ ] Create git tag
- [ ] Push to GitHub

Release:
- [ ] Create GitHub release
- [ ] Upload to test PyPI
- [ ] Test installation from test PyPI
- [ ] Upload to production PyPI
- [ ] Verify package on PyPI
- [ ] Test installation: `pip install blueprint-cli`
- [ ] Announce release

## Success Criteria
- Blueprint can be installed via `pip install blueprint-cli`
- Entry point works: `blueprint --version`
- All features work in installed version
- Package works on macOS, Linux, WSL
- PyPI page displays correctly
- Documentation links work
- Dependencies are properly resolved
- Package size is reasonable (< 1MB)

## Post-Release

### Monitoring

- Watch PyPI download stats
- Monitor GitHub issues
- Track user feedback
- Check compatibility reports

### Maintenance

- Respond to issues quickly
- Release patch versions for bugs
- Keep dependencies updated
- Maintain backward compatibility
