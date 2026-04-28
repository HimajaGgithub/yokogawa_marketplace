#!/usr/bin/env bash

set -euo pipefail

# Directory for logs
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Define services: "name port command"
services=(
  "main 8000 uv run uvicorn src.main:app --host 0.0.0.0 --env-file .env.marketplace --log-config uvicorn_log_config.json"
  "manufacturer 8001 uv run uvicorn src.agent:app --port 8001 --env-file .env.manufacturer --log-config uvicorn_log_config.json"
  "recycler 8002 uv run uvicorn src.agent:app --port 8002 --env-file .env.recycler --log-config uvicorn_log_config.json"
  "recycler_2 8003 uv run uvicorn src.agent:app --port 8003 --env-file .env.recycler_2 --log-config uvicorn_log_config.json"
  "fleet 8004 uv run uvicorn src.agent:app --port 8004 --env-file .env.fleet --log-config uvicorn_log_config.json"
  "manufacturer_2 8005 uv run uvicorn src.agent:app --port 8005 --env-file .env.manufacturer_2 --log-config uvicorn_log_config.json"
  "oem 8006 uv run uvicorn src.agent:app --port 8006 --env-file .env.oem --log-config uvicorn_log_config.json"
  "fleet_2 8007 uv run uvicorn src.agent:app --port 8007 --env-file .env.fleet_2 --log-config uvicorn_log_config.json"
  "oem_2 8008 uv run uvicorn src.agent:app --port 8008 --env-file .env.oem_2 --log-config uvicorn_log_config.json"
  "market_agent 8009 uv run uvicorn src.agent:app --port 8009 --env-file .env.market_agent --log-config uvicorn_log_config.json"
)

# Check if all ports are free before starting any service
echo "Checking all required ports..."
conflicts=()
for svc in "${services[@]}"; do
  read -r name port cmd <<<"$svc"
  if lsof -i ":$port" >/dev/null 2>&1; then
    conflicts+=("$port ($name)")
  fi
done

if [ "${#conflicts[@]}" -ne 0 ]; then
  echo "❌ The following ports are already in use: ${conflicts[*]}"
  echo "Exiting to prevent partial startup."
  exit 1
fi
echo "✅ All ports are free."

# Start services sequentially
for svc in "${services[@]}"; do
  read -r name port cmd <<<"$svc"
  logfile="$LOG_DIR/${port}"
  echo "Launching $name on port $port (logs: $logfile)"

  # Change the redirect from > to >> to append
  nohup $cmd >>"$logfile" 2>&1 &

  # Wait for each service to be ready before starting the next
  echo -n "⏳ Waiting for $name to be ready..."
  timeout=30 # Maximum wait time in seconds
  start_time=$(date +%s)

  while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [[ $elapsed -ge $timeout ]]; then
      echo -e "\033[1K\r❌ $name failed to start within the timeout period."
      echo "Stopping all services and exiting."
      killall uv
      exit 1
    fi

    # Use curl to check a health endpoint with a GET request
    if curl --silent --fail "http://localhost:$port/" >/dev/null; then
      echo -e "\033[1K\r✅ $name is ready!"
      break
    fi
    sleep 1 # Wait before trying again
  done
done

echo "All services started and ready."