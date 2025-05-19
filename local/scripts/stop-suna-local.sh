#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  stop-suna-local.sh — Stop all Suna AI local services
# ---------------------------------------------------------------------------
#  • Stops Suna AI frontend and backend services
#  • Stops Docker services (Supabase, Redis, RabbitMQ)
#  • Stops Daytona sandbox environment
# ---------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# 1) Configuration and paths
# ---------------------------------------------------------------------------
SUNA_HOME="${SUNA_HOME:-$HOME/personal/code/suna}"
PERSONAL_BIN="${PERSONAL_BIN:-$HOME/personal/bin}"
DAYTONA_HOME="${DAYTONA_HOME:-$PERSONAL_BIN}"
DAYTONA_BIN="${DAYTONA_BIN:-$DAYTONA_HOME/daytona}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-$SUNA_HOME/suna/docker-compose.yaml}"
PID_FILE="$SUNA_HOME/.suna_pids"

# ---------------------------------------------------------------------------
# 2) Helper functions
# ---------------------------------------------------------------------------
print_header() {
  echo -e "\n\033[1;36m$1\033[0m"
  echo -e "\033[1;36m${1//?/=}\033[0m"
}

stop_process() {
  local pid=$1
  local name=$2
  
  if ps -p "$pid" > /dev/null; then
    echo "🛑 Stopping $name (PID: $pid)..."
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null
    echo "✅ $name stopped."
  else
    echo "ℹ️ $name (PID: $pid) is not running."
  fi
}

# ---------------------------------------------------------------------------
# 3) Stop Suna AI services
# ---------------------------------------------------------------------------
print_header "Stopping Suna AI Services"

# Load PIDs if available
if [ -f "$PID_FILE" ]; then
  source "$PID_FILE"
  
  # Stop frontend
  if [ -n "${FRONTEND_PID:-}" ]; then
    stop_process "$FRONTEND_PID" "Frontend"
  else
    echo "⚠️ Frontend PID not found."
  fi
  
  # Stop backend
  if [ -n "${BACKEND_PID:-}" ]; then
    stop_process "$BACKEND_PID" "Backend"
  else
    echo "⚠️ Backend PID not found."
  fi
  
  # Remove PID file
  rm -f "$PID_FILE"
else
  echo "⚠️ PID file not found. Attempting to find and stop processes manually..."
  
  # Find and stop frontend process
  FRONTEND_PID=$(pgrep -f "npm run dev" || echo "")
  if [ -n "$FRONTEND_PID" ]; then
    stop_process "$FRONTEND_PID" "Frontend"
  else
    echo "ℹ️ Frontend process not found."
  fi
  
  # Find and stop backend process
  BACKEND_PID=$(pgrep -f "uvicorn api:app" || echo "")
  if [ -n "$BACKEND_PID" ]; then
    stop_process "$BACKEND_PID" "Backend"
  else
    echo "ℹ️ Backend process not found."
  fi
fi

# ---------------------------------------------------------------------------
# 4) Stop Docker services
# ---------------------------------------------------------------------------
print_header "Stopping Docker Services"
echo "🐳 Stopping Supabase, Redis, and RabbitMQ..."

if [ -f "$DOCKER_COMPOSE_FILE" ]; then
  cd "$SUNA_HOME"
  docker-compose -f "$DOCKER_COMPOSE_FILE" down
  echo "✅ Docker services stopped."
else
  echo "⚠️ Docker Compose file not found at $DOCKER_COMPOSE_FILE"
  echo "   Attempting to stop containers manually..."
  
  # Stop Supabase containers
  SUPABASE_CONTAINERS=$(docker ps --filter "name=supabase" -q)
  if [ -n "$SUPABASE_CONTAINERS" ]; then
    docker stop $SUPABASE_CONTAINERS
    echo "✅ Supabase containers stopped."
  else
    echo "ℹ️ No Supabase containers found."
  fi
  
  # Stop Redis container
  REDIS_CONTAINER=$(docker ps --filter "name=redis" -q)
  if [ -n "$REDIS_CONTAINER" ]; then
    docker stop $REDIS_CONTAINER
    echo "✅ Redis container stopped."
  else
    echo "ℹ️ No Redis container found."
  fi
  
  # Stop RabbitMQ container
  RABBITMQ_CONTAINER=$(docker ps --filter "name=rabbitmq" -q)
  if [ -n "$RABBITMQ_CONTAINER" ]; then
    docker stop $RABBITMQ_CONTAINER
    echo "✅ RabbitMQ container stopped."
  else
    echo "ℹ️ No RabbitMQ container found."
  fi
fi

# ---------------------------------------------------------------------------
# 5) Stop Daytona
# ---------------------------------------------------------------------------
print_header "Stopping Daytona"
echo "⏹️ Stopping Daytona daemon..."

if command -v "$DAYTONA_BIN" >/dev/null 2>&1; then
  "$DAYTONA_BIN" server stop
  echo "✅ Daytona stopped."
else
  echo "⚠️ Daytona binary not found at $DAYTONA_BIN"
  echo "   Please stop Daytona manually if it's running."
fi

# Stop frps container
FRPS_CONTAINER=$(docker ps --filter "name=frps" -q)
if [ -n "$FRPS_CONTAINER" ]; then
  echo "🛑 Stopping frps container..."
  docker stop $FRPS_CONTAINER
  echo "✅ frps container stopped."
else
  echo "ℹ️ No frps container found."
fi

# ---------------------------------------------------------------------------
# 6) Summary
# ---------------------------------------------------------------------------
print_header "Shutdown Complete"
echo "✅ All Suna AI services have been stopped."
echo ""
echo "To start the services again, run: ./start-suna-local.sh"
echo ""
