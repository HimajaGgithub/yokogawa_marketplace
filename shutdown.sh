#!/usr/bin/env bash

set -euo pipefail

# Define the ports of the services to be shut down
ports=(8000 8001 8002 8003 8004 8005 8006 8007 8008 8009)

echo "Shutting down services..."

for port in "${ports[@]}"; do
  # Find the PIDs of the processes listening on the port
  echo -n "Scanning port $port..."
  pids=$(lsof -nP -t -iTCP:"$port" -sTCP:LISTEN || true)

  if [ -n "$pids" ]; then
    # Use a for loop to iterate over each PID and kill it
    for pid in $pids; do
      echo -e "\033[1K\r✅ Found process with PID $pid on port $port. Attempting to shut down..."
      # Attempt a graceful shutdown first (SIGTERM)
      kill "$pid" || true
    done

    # Give processes time to shut down gracefully
    sleep 3

    # Check if any of the processes are still running and force kill them
    for pid in $pids; do
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "Process with PID $pid on port $port did not shut down gracefully. Force killing..."
        kill -9 "$pid" || true
        echo "Force killed PID $pid."
      fi
    done
  fi
done

echo "Service shutdown complete."