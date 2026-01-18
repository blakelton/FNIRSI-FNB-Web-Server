# FNIRSI Web Monitor - Makefile
# Common development and deployment commands

.PHONY: help install install-dev install-full run test lint format clean docs

# Default target
help:
	@echo "FNIRSI Web Monitor - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install      - Install minimal dependencies (standalone monitor)"
	@echo "  make install-full - Install all dependencies (professional mode)"
	@echo "  make install-dev  - Install development dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make run          - Run the standalone monitor"
	@echo "  make run-pro      - Run the professional mode app"
	@echo ""
	@echo "Development:"
	@echo "  make test         - Run test suite"
	@echo "  make lint         - Run linter (flake8)"
	@echo "  make format       - Format code (black)"
	@echo "  make clean        - Remove build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run in Docker container"

# Setup virtual environment if not exists
venv:
	python3 -m venv venv

# Install minimal dependencies
install: venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements-minimal.txt

# Install all dependencies
install-full: venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt

# Install development dependencies
install-dev: install-full
	. venv/bin/activate && pip install pytest pytest-cov black flake8

# Run standalone monitor
run:
	. venv/bin/activate && python fnb48p_monitor.py

# Run professional mode
run-pro:
	. venv/bin/activate && python app.py

# Run tests
test:
	. venv/bin/activate && pytest tests/ -v

# Run tests with coverage
test-cov:
	. venv/bin/activate && pytest tests/ -v --cov=. --cov-report=html

# Lint code
lint:
	. venv/bin/activate && flake8 fnb48p_monitor.py app.py device/ --max-line-length=100

# Format code
format:
	. venv/bin/activate && black fnb48p_monitor.py app.py device/ --line-length=100

# Clean build artifacts
clean:
	rm -rf __pycache__/
	rm -rf device/__pycache__/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf *.egg-info/
	rm -rf dist/
	rm -rf build/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Docker commands
docker-build:
	docker build -t fnirsi-web-monitor .

docker-run:
	docker run -p 5002:5002 --privileged fnirsi-web-monitor

# Development server with auto-reload (requires watchdog)
dev:
	. venv/bin/activate && FLASK_ENV=development python fnb48p_monitor.py
