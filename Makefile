.PHONY: install test lint format typecheck check clean dev-install demo help
.DEFAULT_GOAL := help

## Development Commands

install: ## Install the package in development mode
	uv pip install -e ".[dev]"

sync: ## Install from uv.lock (recommended)
	uv sync

dev-install: ## Install with all optional dependencies
	uv pip install -e ".[dev,openai,openrouter]"

test: ## Run tests
	pytest

lint: ## Run linting
	ruff check src/ tests/ programs/

format: ## Format code
	ruff format src/ tests/ programs/

typecheck: ## Run type checking
	mypy

check: ## Run all checks (lint, format, typecheck, test)
	@echo "=== Linting ==="
	ruff check src/ tests/ programs/
	@echo "=== Format check ==="
	ruff format --check src/ tests/ programs/
	@echo "=== Type checking ==="
	mypy
	@echo "=== Tests ==="
	pytest

clean: ## Clean build artifacts and cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	find . -name ".mypy_cache" -type d -exec rm -rf {} +
	find . -name ".ruff_cache" -type d -exec rm -rf {} +
	find . -name "*.egg-info" -type d -exec rm -rf {} +
	rm -rf build/ dist/

demo: ## Show available demo commands
	@echo "Available demos:"
	@echo "  python -m llmgine.engines.single_pass_engine  # Pirate translator"
	@echo "  python -m llmgine.engines.tool_chat_engine    # Tool-enabled chat"
	@echo ""
	@echo "Make sure you have set your API keys in .env file!"

## Pre-commit setup

pre-commit-install: ## Install pre-commit hooks
	pre-commit install

pre-commit-run: ## Run pre-commit on all files
	pre-commit run --all-files


help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'