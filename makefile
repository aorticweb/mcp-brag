# UV commands
install:
	uv sync --extra server --extra embedder --extra dev

install-server:
	uv sync --extra server --extra embedder

install-dev:
	uv sync --extra dev

update:
	uv lock --upgrade

# Clean and reinstall
clean:
	rm -rf .venv
	uv sync --all-extras

format:
	uv run isort --atomic --profile black --apply ./common ./embedder ./server ./tests
	uv run black ./common ./embedder ./server ./tests
	cd ui && npm run format

lint:
	uv run isort --check --profile black ./common ./embedder ./server ./tests
	uv run black --check ./common ./embedder ./server ./tests
	uv run mypy ./common ./embedder ./server ./tests
	uv run flake8 ./common ./embedder ./server ./tests
	cd ui && npm run lint

pytest_args := 
unit-test:
	uv run pytest --ignore=ui $(pytest_args)

gen-server-client:
	npx @hey-api/openapi-ts \
	-i ./docs/openapi.yaml \
	-o ./ui/src/server-client
	cd ui && npm run format

run-server:
	uv run python -m server.main

run-ui-app-dev:
	cd ui && npm run dev

package-app:
	cd ui && npm run make

build: build-server package-app

copy-python-env:
	./copy-python-interprater.sh

# Build server executable with shiv
build-server: install-server
	@echo "Building server executable with shiv..."
	@mkdir -p dist
	uv run shiv \
		--site-packages .venv/lib/python3.12/site-packages \
		--compressed \
		--entry-point server.main:main \
		--output-file dist/mcp_server.pyz \
		--python '/usr/bin/env python3' \
		--upgrade \
		.
	@echo "Server executable built at: ./dist/mcp_server.pyz"
	./copy-python-interprater.sh
	cp ./dist/python-standalone/bin/python ./ui/server-dist/
	cp ./dist/mcp_server.pyz ./ui/server-dist/
	rm -rf ./dist/python-standalone


# Test the built executable
run-server-executable:
	./ui/server-dist/python ./ui/server-dist/mcp_server.pyz

help:
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies with all extras"
	@echo "  make install-server   - Install server and embedder dependencies"
	@echo "  make install-agent    - Install agent dependencies"
	@echo "  make install-dev      - Install dev dependencies only"
	@echo "  make update           - Update and lock all dependencies"
	@echo "  make clean            - Clean environment and reinstall"
	@echo "  make clean-build      - Clean build artifacts"
	@echo "  make format           - Format code"
	@echo "  make lint             - Lint code"
	@echo "  make unit-test        - Run tests"
	@echo "  make unit-test-with-cov - Run tests with coverage"
	@echo "  make run-server       - Run the server"
	@echo "  make build            - Build the complete application"
	@echo "  make build-server     - Build server executable with shiv"
	@echo "  make test-executable  - Test the built executable"