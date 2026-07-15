# Justfile — Better Dontforget development workflow
#
# Canonical quality gate: `just check`

# Show available recipes.
default:
    @just --list

# Install dependencies (uv-managed virtual environment).
install:
    uv sync

# Build a distributable wheel/sdist.
build:
    uv build

# Run the application (opens TUI when no arguments are given).
run *ARGS:
    uv run better-dontforget {{ARGS}}

# Format all Python sources.
fmt:
    uv run ruff format .

# Lint (ruff check).
lint:
    uv run ruff check .

# Type-check (mypy) on the package.
type:
    uv run mypy better_dontforget

# Run the test suite.
test:
    uv run pytest

# Canonical full-project verification.
check:
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy better_dontforget
    uv run pytest
    uv build
