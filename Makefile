.PHONY: help install setup dev-setup clean test run dev lint format check env-setup dirs all

# Python and pip executables
PYTHON := python3
PIP := pip3
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

# Default target
help:
	@echo "Available targets:"
	@echo "  setup         - Complete project setup (create venv, install deps, setup env)"
	@echo "  dev-setup     - Development setup with additional dev dependencies"
	@echo "  install       - Install dependencies in existing environment"
	@echo "  env-setup     - Setup environment variables and directories"
	@echo "  dirs          - Create necessary directories"
	@echo "  clean         - Clean up build artifacts and cache"
	@echo "  test          - Run tests"
	@echo "  run           - Run the FastAPI application"
	@echo "  dev           - Run development server with auto-reload"
	@echo "  lint          - Run linting (flake8, if available)"
	@echo "  format        - Format code (black, if available)"
	@echo "  check         - Run all checks (lint, test)"
	@echo "  requirements  - Generate/update requirements.txt from current environment"
	@echo "  all           - Complete setup and run tests"
	@echo ""
	@echo "Plaid Integration:"
	@echo "  plaid-link-token USER_ID=<id>  - Create link token for bank account connection"
	@echo "  plaid-sync                     - Sync transactions for all linked accounts"
	@echo "  plaid-accounts                 - List all linked bank accounts"
	@echo "  plaid-transactions USER_ID=<id> - Show transactions for user"
	@echo "  plaid-summary USER_ID=<id>     - Show transaction summary for user"
	@echo ""
	@echo "Airbyte Integration:"
	@echo "  airbyte-check     - Check Airbyte dependencies and status"
	@echo "  airbyte-start     - Start Airbyte and Plaid API services"
	@echo "  airbyte-stop      - Stop all Airbyte services"
	@echo "  airbyte-status    - Show service status and data statistics"
	@echo "  airbyte-sync      - Trigger Plaid data sync"
	@echo "  airbyte-setup     - Set up Airbyte connections and sources"
	@echo "  airbyte-logs      - Show Airbyte service logs"
	@echo "  airbyte-init      - Complete Airbyte initialization"

# Create virtual environment
$(VENV):
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created at $(VENV)/"

# Install dependencies
install: $(VENV)
	@echo "Installing dependencies..."
	$(VENV_PIP) install --upgrade pip setuptools wheel
	$(VENV_PIP) install -r requirements.txt
	@echo "Dependencies installed successfully!"

# Development setup with additional tools
dev-setup: $(VENV)
	@echo "Setting up development environment..."
	$(VENV_PIP) install --upgrade pip setuptools wheel
	$(VENV_PIP) install -r requirements.txt
	$(VENV_PIP) install pytest black flake8 isort pre-commit
	@echo "Development environment setup complete!"

# Setup environment variables and directories
env-setup:
	@echo "Setting up environment..."
	@if [ ! -f .env ]; then \
		echo "Copying .env.example to .env..."; \
		cp .env.example .env; \
		echo "Please edit .env file with your configuration"; \
	else \
		echo ".env file already exists"; \
	fi

# Create necessary directories
dirs:
	@echo "Creating directories..."
	@mkdir -p data/audio_uploads
	@mkdir -p data/uploads
	@mkdir -p dhi.core/data/chart_uploads
	@mkdir -p dhi.core/data/image_uploads
	@mkdir -p dhi.core/data/text_uploads
	@mkdir -p logs
	@echo "Directories created successfully!"

# Complete project setup
setup: $(VENV) install env-setup dirs
	@echo "Project setup completed successfully!"
	@echo ""
	@echo "To activate the virtual environment, run:"
	@echo "  source $(VENV_BIN)/activate"
	@echo ""
	@echo "To run the application:"
	@echo "  make run"

# Clean up build artifacts and cache
clean:
	@echo "Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/
	@rm -rf dist/
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@echo "Cleanup completed!"

# Remove virtual environment
clean-venv:
	@echo "Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "Virtual environment removed!"

# Full clean (including virtual environment)
clean-all: clean clean-venv
	@echo "Full cleanup completed!"

# Run tests
test: $(VENV)
	@echo "Running tests..."
	$(VENV_PYTHON) -m pytest tests/ -v
	@echo "Tests completed!"

# Run the FastAPI application
run: $(VENV)
	@echo "Starting FastAPI application..."
	$(VENV_PYTHON) -m uvicorn dhi.core.api.app:app --host 0.0.0.0 --port 8000

# Run development server with auto-reload
dev: $(VENV)
	@echo "Starting development server..."
	$(VENV_PYTHON) -m uvicorn dhi.core.api.app:app --host 0.0.0.0 --port 8000 --reload

# Run linting
lint: $(VENV)
	@echo "Running linting..."
	@if $(VENV_PYTHON) -c "import flake8" 2>/dev/null; then \
		$(VENV_BIN)/flake8 dhi.core/ ingestion/ transcription/ tests/ --max-line-length=88 --ignore=E203,W503; \
	else \
		echo "flake8 not installed, run 'make dev-setup' for development tools"; \
	fi

# Format code
format: $(VENV)
	@echo "Formatting code..."
	@if $(VENV_PYTHON) -c "import black" 2>/dev/null; then \
		$(VENV_BIN)/black dhi.core/ ingestion/ transcription/ tests/; \
		echo "Code formatted with black"; \
	else \
		echo "black not installed, run 'make dev-setup' for development tools"; \
	fi
	@if $(VENV_PYTHON) -c "import isort" 2>/dev/null; then \
		$(VENV_BIN)/isort dhi.core/ ingestion/ transcription/ tests/; \
		echo "Imports sorted with isort"; \
	else \
		echo "isort not installed, run 'make dev-setup' for development tools"; \
	fi

# Run all checks
check: lint test
	@echo "All checks completed successfully!"

# Generate requirements.txt from current environment
requirements: $(VENV)
	@echo "Generating requirements.txt..."
	$(VENV_PIP) freeze > requirements-freeze.txt
	@echo "Current environment frozen to requirements-freeze.txt"

# Install package in development mode
install-dev: $(VENV)
	@echo "Installing package in development mode..."
	$(VENV_PIP) install -e .

# Run specific test file
test-file: $(VENV)
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make test-file FILE=tests/test_filename.py"; \
	else \
		$(VENV_PYTHON) -m pytest $(FILE) -v; \
	fi

# Show Python and package versions
versions: $(VENV)
	@echo "Python version:"
	@$(VENV_PYTHON) --version
	@echo ""
	@echo "Key package versions:"
	@$(VENV_PYTHON) -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')" 2>/dev/null || echo "FastAPI: not installed"
	@$(VENV_PYTHON) -c "import sqlalchemy; print(f'SQLAlchemy: {sqlalchemy.__version__}')" 2>/dev/null || echo "SQLAlchemy: not installed"
	@$(VENV_PYTHON) -c "import torch; print(f'PyTorch: {torch.__version__}')" 2>/dev/null || echo "PyTorch: not installed"

# Complete setup and verification
all: setup test
	@echo "Project setup and verification completed successfully!"
	@echo ""
	@echo "Your project is ready to use!"
	@echo "Activate the virtual environment: source $(VENV_BIN)/activate"
	@echo "Start development server: make dev"

# Add plaid script to Makefile
plaid-link-token: $(VENV)
	@if [ -z "$(USER_ID)" ]; then \
		echo "Usage: make plaid-link-token USER_ID=your_user_id"; \
	else \
		$(VENV_PYTHON) scripts/plaid_script.py create-link-token $(USER_ID); \
	fi

plaid-sync: $(VENV)
	@echo "Syncing all Plaid accounts..."
	$(VENV_PYTHON) scripts/plaid_script.py sync-all

plaid-accounts: $(VENV)
	@echo "Listing linked bank accounts..."
	$(VENV_PYTHON) scripts/plaid_script.py list-accounts

plaid-transactions: $(VENV)
	@if [ -z "$(USER_ID)" ]; then \
		echo "Usage: make plaid-transactions USER_ID=your_user_id"; \
	else \
		$(VENV_PYTHON) scripts/plaid_script.py get-transactions $(USER_ID); \
	fi

plaid-summary: $(VENV)
	@if [ -z "$(USER_ID)" ]; then \
		echo "Usage: make plaid-summary USER_ID=your_user_id"; \
	else \
		$(VENV_PYTHON) scripts/plaid_script.py summary $(USER_ID); \
	fi

# Airbyte Integration Commands
# airbyte-check: $(VENV)
# 	@echo "Checking Airbyte dependencies and status..."
# 	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py check

airbyte-start: $(VENV)
	@echo "Starting Airbyte and Plaid API services..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py start

airbyte-stop: $(VENV)
	@echo "Stopping Airbyte services..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py stop

airbyte-status: $(VENV)
	@echo "Checking Airbyte service status..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py status

airbyte-sync: $(VENV)
	@echo "Triggering Plaid data sync..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py sync

airbyte-setup: $(VENV)
	@echo "Setting up Airbyte connections..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py setup

airbyte-logs: $(VENV)
	@echo "Showing Airbyte logs..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py logs

airbyte-init: $(VENV)
	@echo "Initializing complete Airbyte setup..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py init

airbyte-test: $(VENV)
	@echo "Running Airbyte integration tests..."
	$(VENV_PYTHON) scripts/test_airbyte_integration.py


# Test data setup
.PHONY: setup-test-data clean-test-data

setup-test-data: $(VENV)
	@echo "Setting up test data for Plaid integration..."
	$(VENV_PYTHON) scripts/setup_test_data.py

clean-test-data: $(VENV)
	@echo "Cleaning up test data..."
	$(VENV_PYTHON) scripts/setup_test_data.py clean

# Update airbyte-check to include test data setup
airbyte-check: $(VENV)
	@echo "Checking Airbyte dependencies and status..."
	$(VENV_PYTHON) scripts/plaid_airbyte_manager.py check
	@echo "Setting up test data if needed..."
	@make setup-test-data