.PHONY: install lint fmt test run docker-build docker-run

install: ## Install dependencies with Poetry
	@poetry install

lint: ## Run linting with pylint and formatting with black
	@poetry run pylint core agents app.py
	@poetry run black --check core agents tests app.py frontend
	@poetry run isort --check-only core agents tests app.py frontend

fmt: ## Auto-format code with black and isort
	@poetry run black core agents tests app.py frontend
	@poetry run isort core agents tests app.py frontend

test: ## Run tests with pytest and coverage
	@poetry run pytest --maxfail=1 --disable-warnings -q --cov=.

run: ## Run the Flask app
	@poetry run python app.py

docker-build: ## Build Docker image
	@docker build -t security-scanner .

docker-run: ## Run Docker container
	@docker run -p 5000:5000 security-scanner
