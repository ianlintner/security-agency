.PHONY: install lint test run docker-build docker-run

install: ## Install dependencies with Poetry
	@poetry install

lint: ## Run linting with pylint
	@poetry run pylint core agents app.py

test: ## Run tests with pytest and coverage
	@poetry run pytest --maxfail=1 --disable-warnings -q --cov=.

run: ## Run the Flask app
	@poetry run python app.py

docker-build: ## Build Docker image
	@docker build -t security-scanner .

docker-run: ## Run Docker container
	@docker run -p 5000:5000 security-scanner
