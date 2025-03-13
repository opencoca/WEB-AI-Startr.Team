help: 
	@echo "================================================"
	@echo "================================================"
	@echo "    Startr/WEB-AI-Startr.Team by Startr.Cloud   "
	@echo "================================================"
	@echo "================================================"
	@echo "This is the default make command."
	@echo "This command lists available make commands."
	@echo ""
	@echo "Usage example:"
	@echo "    make it_run"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'
	@echo ""

# Debug targets
debug-setup:
	@echo "Setting up debugging environment"
	@chmod +x debug_run.py
	@echo "Debug environment setup complete"

debug-run:
	@echo "Running with debugging enabled"
	@python -m startr.team.debug_run --model-debug --interactive --log-level info

debug-model:
	@echo "Running model verification"
	@python -m startr.team.debug_run --check-model --model $(MODEL)

debug-inspect:
	@echo "Running with interactive debugging and breakpoints"
	@python -m startr.team.debug_run --interactive --breakpoints "OpenAIModel.run,ChatChain.execute_chain,Phase.execute" --model-debug

debug-fallback:
	@echo "Running with fallback model (GPT-4)"
	@python -m startr.team.debug_run --model GPT_4 --model-debug

debug-api-test:
	@echo "Testing API connectivity with minimal request"
	@python -c "import os, openai; client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY']); print(client.chat.completions.create(model='gpt-3.5-turbo', messages=[{'role': 'user', 'content': 'Hello'}], max_tokens=5))"

debug-help:
	@echo "Debug targets:"
	@echo "  debug-setup     - Set up debugging environment"
	@echo "  debug-run       - Run with debugging enabled"
	@echo "  debug-model     - Run model verification (use MODEL=model_name)"
	@echo "  debug-inspect   - Run with interactive debugging and breakpoints"
	@echo "  debug-fallback  - Run with fallback model (GPT-4)"
	@echo "  debug-api-test  - Test API connectivity with minimal request"
	@echo "  debug-help      - Show this help message"
	@echo ""
	@echo "Example usage:"
	@echo "  make debug-model MODEL=LLAMA_3"
	@echo "  make debug-run"

# Add debug targets to help
help: debug-help

minor_release:
	git flow release start $$(git describe --tags --abbrev=0 | awk -F'[v.]' '{print $$2"."$$3+1".0"}').$$(date +'_%Y-%m-%d')

patch_release:
	git flow release start $$(git describe --tags --abbrev=0 | awk -F'[v.]' '{print $$2"."$$3"."$$4+1}').$$(date +'_%Y-%m-%d')

major_release:
	git flow release start $$(git describe --tags --abbrev=0 | awk -F'[v.]' '{print $$2+1".0.0"}').$$(date +'_%Y-%m-%d')

release_finish:
	git flow release finish "$$(git branch --show-current | sed 's/release\///')" && git push origin develop && git push origin main && git push --tags && git checkout develop

hotfix:
	git flow hotfix start $$(git describe --tags --abbrev=0 | awk -F'[v.]' '{print $$2"."$$3"."$$4+1}').$$(date +'_%Y-%m-%d')

hotfix_finish:
	git flow hotfix finish "$$(git branch --show-current | sed 's/hotfix\///')" && git push origin develop && git push origin main && git push --tags && git checkout develop

clean_git_repo:
	git clean --exclude=!.env -Xdf


it_run:
	@bash -c 'bash <(curl -sL startr.sh) run'

it_build:
	@bash -c 'bash <(curl -sL startr.sh) build'

# ==========================================================================
# MAINTENANCE TASKS
# ==========================================================================
# IMPORTANT: Always add reusable operations to the Makefile as targets.
# This ensures:
# 1. Documentation of common tasks
# 2. Reproducibility across environments
# 3. Consistent execution of complex operations
# 4. Easy onboarding for new team members

# Fix JSON syntax errors in configuration files by removing comments
# This is needed because standard JSON doesn't support comments
fix-json-configs:
	@echo "Creating backups of original configuration files..."
	@cp config/CompanyConfig/Default/ChatChainConfig.json config/CompanyConfig/Default/ChatChainConfig.json.bak
	@echo "Removing comments from JSON configuration files..."
	@cat config/CompanyConfig/Default/ChatChainConfig.json | grep -v '//' | jq . > fixed_config.json
	@cp fixed_config.json config/CompanyConfig/Default/ChatChainConfig.json
	@echo "Fixed JSON configuration files. Originals backed up with .bak extension."

# Same operation for Docker environment
docker-fix-json-configs:
	@echo "Fixing JSON configuration files in Docker container..."
	docker exec -it web-ai-startr.team-develop bash -c "cd /project && \
		cp config/CompanyConfig/Default/ChatChainConfig.json config/CompanyConfig/Default/ChatChainConfig.json.bak && \
		cat config/CompanyConfig/Default/ChatChainConfig.json | grep -v '//' | jq . > fixed_config.json && \
		cp fixed_config.json config/CompanyConfig/Default/ChatChainConfig.json"
	@echo "Fixed JSON configuration files in Docker container."

# ==========================================================================
# API KEY MANAGEMENT
# ==========================================================================
# Create a default .env file from the example if one doesn't exist
init-env:
	@if [ ! -f .env ]; then \
		echo "Creating .env file from .env.example..."; \
		cp .env.example .env; \
		echo "Please edit .env file to add your API keys"; \
	else \
		echo ".env file already exists"; \
	fi

# Update Docker container with API keys from .env file
docker-update-keys:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make init-env' first."; \
		exit 1; \
	fi
	@echo "Updating Docker container with API keys from .env file..."
	@export $$(grep -v '^#' .env | xargs) && \
	docker exec -it web-ai-startr.team-develop bash -c "cd /project && \
		echo 'export OPENAI_API_KEY=\"$$OPENAI_API_KEY\"' > /project/.env && \
		echo 'export GROQ_API_KEY=\"$$GROQ_API_KEY\"' >> /project/.env && \
		echo 'API keys updated in container'"
	@echo "Docker container API keys updated. Run 'make docker-restart' to apply changes."

# One command to update keys and restart the container's processes
docker-update-and-restart: docker-update-keys docker-restart

# Restart the application inside Docker to use new API keys
# The nohup command is used to run the application in the background
# and allows it to continue running even after the terminal is closed.
docker-restart:
	@echo "Restarting application inside Docker container..."
	@docker exec -it web-ai-startr.team-develop bash -c "cd /project && \
		pkill -f 'python' || true && \
		source .env && \
		nohup python visualizer/app.py --port 5000 > /dev/null 2>&1 &"
	@echo "Application restarted with updated API keys."

# Open a shell in the running Docker container
shell:
	@echo "Opening a shell in the Docker container..."
	@docker exec -it web-ai-startr.team-develop bash -c "source /project/.env && exec bash"

# Run inside Docker with direct logging to the host machine 
docker-run-with-log:
	@echo "Running in Docker with logging to WareHouse/docker_run_$(shell date +%Y%m%d_%H%M%S).log..."
	@mkdir -p WareHouse/docker_run_$(shell date +%Y%m%d_%H%M%S)
	@docker exec -it web-ai-startr.team-develop bash -c "cd /project && source /project/.env && python -m strteam" | tee WareHouse/docker_run_$(shell date +%Y%m%d_%H%M%S)/output.log

# Verify that API keys are working properly
verify-api-keys:
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Run 'make init-env' first."; \
		exit 1; \
	fi
	@echo "Verifying OpenAI API key..."
	@export $$(grep -v '^#' .env | xargs) && \
	curl -s "https://api.openai.com/v1/chat/completions" \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $$OPENAI_API_KEY" \
		-d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}' | head -20
	@echo "\nAPI key verification completed."

# Verify API keys inside Docker container
docker-verify-api-keys:
	@echo "Verifying OpenAI API key in Docker container..."
	@docker exec -it web-ai-startr.team-develop bash -c "cd /project && \
		source .env && \
		curl -s 'https://api.openai.com/v1/chat/completions' \
			-H 'Content-Type: application/json' \
			-H 'Authorization: Bearer \$$OPENAI_API_KEY' \
			-d '{\"model\": \"gpt-4o-mini\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello\"}]}' | head -20"
	@echo "\nAPI key verification in Docker completed."

# ==========================================================================
# VISUALIZATION TOOLS
# ==========================================================================
# Start visualizer locally for testing
run-visualizer:
	@echo "Starting visualizer on http://localhost:8080..."
	python visualizer/app.py --port 8080

# Direct run with guaranteed logging
run-with-log:
	@echo "Running with direct logging to output.log..."
	@mkdir -p WareHouse/$(shell date +%Y%m%d_%H%M%S)_run
	@python -m startr.team | tee WareHouse/$(shell date +%Y%m%d_%H%M%S)_run/output.log

# List all WareHouse projects with log files
list-logs:
	@echo "Available log files in WareHouse directory:"
	@find WareHouse -name "*.log" | sort

# Check a specific log file's format
check-log-format:
	@if [ -z "$(LOG_FILE)" ]; then \
		echo "Error: Please specify a log file with LOG_FILE=path/to/logfile.log"; \
		exit 1; \
	fi
	@echo "Analyzing log format for $(LOG_FILE)..."
	@head -n 50 $(LOG_FILE) | grep -E '^\[[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -n 5
	@echo "\nLog type: Docker format"
	@echo "Use the replay tool at http://localhost:8080/replay to visualize this log"

# Fix visualization in Docker container
docker-fix-visualization:
	@echo "Updating visualization files in Docker container..."
	@docker exec -it web-ai-startr.team-develop bash -c "cd /project && \
		sed -i 's/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (.*?)\$$/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+)\] (.*)\$$/g' visualizer/static/replay/js/app.js && \
		sed -i 's/Startr.Team Starts/\*\*Startr\\.Team Starts\*\*/g' visualizer/static/replay/js/app.js && \
		sed -i 's/task_prompt: (.*)/\*\*task_prompt\*\*: (.*)/g' visualizer/static/replay/js/app.js"
	@echo "Visualization files updated. Restart the visualizer with 'make docker-restart'"

# Restart visualizer to apply changes
docker-restart-visualizer: docker-fix-visualization docker-restart

# Docker-specific targets
docker-run:
	@echo "Running WEB-AI-Startr.Team in Docker..."
	@bash -c 'bash <(curl -sL startr.sh) run'

docker-debug:
	@echo "Running debug commands in Docker container..."
	@docker exec -it web-ai-startr.team-develop python -m startr.team.debug_run --model-debug --interactive --log-level info

docker-shell:
	@echo "Opening a shell in the Docker container..."
	@docker exec -it web-ai-startr.team-develop bash

docker-test-model:
	@echo "Testing model in Docker container..."
	@docker exec -it web-ai-startr.team-develop python -m startr.team.debug_run --check-model --model $(MODEL)

# Add Docker targets to help
help: 
	@echo "Docker commands:"
	@echo "  docker-run       - Run WEB-AI-Startr.Team in Docker (recommended)"
	@echo "  docker-debug     - Run debugging tools in Docker"
	@echo "  docker-shell     - Open a shell in the Docker container"
	@echo "  docker-test-model- Test a model in Docker (use MODEL=model_name)"
	@echo ""
	@echo "Example: make docker-test-model MODEL=LLAMA_3"
	@echo ""
	@echo "IMPORTANT: Docker is the recommended way to run this project"
	@echo ""
