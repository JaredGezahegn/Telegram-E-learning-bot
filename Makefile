.PHONY: install test clean run setup

# Setup virtual environment and install dependencies
setup:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  (Linux/Mac)"
	@echo "  venv\\Scripts\\activate     (Windows)"

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	python -m pytest tests/ -v

# Run property-based tests
test-pbt:
	python -m pytest tests/ -v -k "property"

# Clean up generated files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/

# Run the bot
run:
	python -m src.main

# Check code style
lint:
	flake8 src/ tests/

# Format code
format:
	black src/ tests/