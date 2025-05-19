#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  start-suna-local.sh — Complete Suna AI local startup script
# ---------------------------------------------------------------------------
#  • Starts Daytona sandbox environment
#  • Launches Supabase, Redis, RabbitMQ via docker-compose
#  • Starts Suna AI backend and frontend services
#  • Assumes Suna AI is in ~/personal/code/suna
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
DAYTONA_SCRIPT="${DAYTONA_SCRIPT:-$PERSONAL_BIN/start-daytona-local.sh}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-$SUNA_HOME/suna/docker-compose.yaml}"
BACKEND_DIR="$SUNA_HOME/suna/backend"
FRONTEND_DIR="$SUNA_HOME/suna/frontend"
LOG_DIR="$SUNA_HOME/logs"

# Environment variables for Suna AI
export DAYTONA_SERVER_URL="http://localhost:3986/api"
export DAYTONA_TARGET="local"
export SUPABASE_URL="http://localhost:54321"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
export REDIS_URL="redis://localhost:6379"
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
export ENV_MODE="local"

# ---------------------------------------------------------------------------
# 2) Helper functions
# ---------------------------------------------------------------------------
print_header() {
  echo -e "\n\033[1;36m$1\033[0m"
  echo -e "\033[1;36m${1//?/=}\033[0m"
}

check_command() {
  command -v "$1" >/dev/null 2>&1 || { echo "❌ $1 is required but not installed."; exit 1; }
}

wait_for_service() {
  local service=$1
  local url=$2
  local max_attempts=$3
  local attempt=1
  
  echo "⏳ Waiting for $service to be ready..."
  while [ $attempt -le $max_attempts ]; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "2[0-9][0-9]\|3[0-9][0-9]"; then
      echo "✅ $service is ready!"
      return 0
    fi
    echo "   Attempt $attempt/$max_attempts: $service not ready yet, waiting..."
    sleep 5
    ((attempt++))
  done
  
  echo "❌ $service failed to start after $max_attempts attempts."
  return 1
}

# ---------------------------------------------------------------------------
# 3) Preconditions
# ---------------------------------------------------------------------------
print_header "Checking prerequisites"

# Check required commands
check_command docker
check_command docker-compose
check_command node
check_command npm
check_command python3
check_command pip3

# Check if Suna AI directory exists
if [ ! -d "$SUNA_HOME" ]; then
  echo "❌ Suna AI directory not found at $SUNA_HOME"
  echo "   Please set SUNA_HOME environment variable or install Suna AI at the default location."
  exit 1
fi

# Check if Daytona script exists
if [ ! -f "$DAYTONA_SCRIPT" ]; then
  echo "❌ Daytona startup script not found at $DAYTONA_SCRIPT"
  echo "   Please set DAYTONA_SCRIPT environment variable or create the script at the default location."
  exit 1
fi

# Check if docker-compose file exists
if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
  echo "❌ Docker Compose file not found at $DOCKER_COMPOSE_FILE"
  echo "   Please set DOCKER_COMPOSE_FILE environment variable or create the file at the default location."
  exit 1
fi

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# ---------------------------------------------------------------------------
# 4) Start Daytona
# ---------------------------------------------------------------------------
print_header "Starting Daytona"
bash "$DAYTONA_SCRIPT"

# ---------------------------------------------------------------------------
# 5) Start Docker services (Supabase, Redis, RabbitMQ)
# ---------------------------------------------------------------------------
print_header "Starting Docker services"
echo "🐳 Starting Supabase, Redis, and RabbitMQ..."
cd "$SUNA_HOME"
docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

# Wait for services to be ready
wait_for_service "Supabase" "$SUPABASE_URL" 12
wait_for_service "Redis" "http://localhost:6379" 6
wait_for_service "RabbitMQ" "http://localhost:15672" 12

# ---------------------------------------------------------------------------
# 6) Start Suna AI Backend
# ---------------------------------------------------------------------------
print_header "Starting Suna AI Backend"
echo "🚀 Starting Suna AI backend service..."
cd "$BACKEND_DIR"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
  echo "🔧 Creating Python virtual environment..."
  python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing backend dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Start backend service
echo "🚀 Launching backend service..."
nohup python -m uvicorn api:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started with PID: $BACKEND_PID"
echo "   Logs available at: $LOG_DIR/backend.log"

# Wait for backend to be ready
wait_for_service "Suna AI Backend" "http://localhost:8000/api/health" 12

# Deactivate virtual environment
deactivate

# ---------------------------------------------------------------------------
# 7) Start Suna AI Frontend
# ---------------------------------------------------------------------------
print_header "Starting Suna AI Frontend"
echo "🚀 Starting Suna AI frontend service..."
cd "$FRONTEND_DIR"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  npm install
fi

# Start frontend service
echo "🚀 Launching frontend service..."
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started with PID: $FRONTEND_PID"
echo "   Logs available at: $LOG_DIR/frontend.log"

# Wait for frontend to be ready
wait_for_service "Suna AI Frontend" "http://localhost:3000" 12

# ---------------------------------------------------------------------------
# 8) Summary
# ---------------------------------------------------------------------------
print_header "Suna AI Local Environment Ready"
echo "🎉 All services are up and running!"
echo ""
echo "📊 Service endpoints:"
echo "   - Suna AI Frontend: http://localhost:3000"
echo "   - Suna AI Backend: http://localhost:8000"
echo "   - Daytona: http://localhost:3986"
echo "   - Supabase: http://localhost:54321"
echo "   - RabbitMQ Management: http://localhost:15672"
echo ""
echo "📝 Logs:"
echo "   - Backend: $LOG_DIR/backend.log"
echo "   - Frontend: $LOG_DIR/frontend.log"
echo ""
echo "⚠️  To stop all services, run: ./stop-suna-local.sh"
echo ""
echo "Happy coding! 🚀"

# Save PIDs for the stop script
echo "BACKEND_PID=$BACKEND_PID" > "$SUNA_HOME/.suna_pids"
echo "FRONTEND_PID=$FRONTEND_PID" >> "$SUNA_HOME/.suna_pids"
