#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  start-daytona-local.sh  —  Offline Daytona + frps one-liner
# ---------------------------------------------------------------------------
#  • Works on macOS and Linux with Docker running
#  • Creates/uses  $PERSONAL_BIN/frp  for config + Docker volume
#  • Patches Daytona server config.json
#  • Enhanced with better error handling and status reporting
# ---------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# 1) Paths & constants
# ---------------------------------------------------------------------------
PERSONAL_BIN="${PERSONAL_BIN:-$HOME/personal/bin}"
DAYTONA_HOME="${DAYTONA_HOME:-$PERSONAL_BIN}"
DAYTONA_BIN="${DAYTONA_BIN:-$DAYTONA_HOME/daytona}"
FRP_HOME="$PERSONAL_BIN/frp"
FRPS_INI="$FRP_HOME/frps.ini"
FRPS_CONT="frps"
FRPS_PORT=7000
DASH_PORT=7500

CONFIG_MACOS="$HOME/Library/Application Support/daytona/server/config.json"
CONFIG_LINUX="$HOME/.config/daytona/server/config.json"
CONFIG_FILE=""

# ---------------------------------------------------------------------------
# 2) Helper functions
# ---------------------------------------------------------------------------
print_header() {
  echo -e "\n\033[1;36m$1\033[0m"
  echo -e "\033[1;36m${1//?/=}\033[0m"
}

check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo "❌ $1 is not installed. Please install it first."
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# 3) Preconditions
# ---------------------------------------------------------------------------
print_header "Checking Prerequisites"

# Check for required commands
check_command "docker"
check_command "jq"

# Check Docker is running
if ! docker info &> /dev/null; then
  echo "❌ Docker is not running. Please start Docker first."
  exit 1
fi

# Determine config file location based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  CONFIG_FILE="$CONFIG_MACOS"
else
  CONFIG_FILE="$CONFIG_LINUX"
fi

# Check if Daytona is installed
if [ ! -f "$DAYTONA_BIN" ]; then
  echo "❌ Daytona CLI not found at $DAYTONA_BIN"
  echo "   Please run setup_daytona_local.sh first."
  exit 1
fi

# Check if frps.ini exists
if [ ! -f "$FRPS_INI" ]; then
  echo "❌ frps.ini not found at $FRPS_INI"
  echo "   Please run setup_daytona_local.sh first."
  exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ Daytona config not found at $CONFIG_FILE"
  echo "   Please run setup_daytona_local.sh first."
  exit 1
fi

echo "✅ All prerequisites are met."

# ---------------------------------------------------------------------------
# 4) Start frps container
# ---------------------------------------------------------------------------
print_header "Starting FRP Server"

echo "🔄 Checking frps container status..."
if docker ps -a --format '{{.Names}}' | grep -q "^${FRPS_CONT}$"; then
  echo "🐳 Restarting frps container..."
  if ! docker restart "$FRPS_CONT" >/dev/null; then
    echo "⚠️  Failed to restart frps container. Removing and recreating..."
    docker rm -f "$FRPS_CONT" >/dev/null 2>&1 || true
    docker run -d --restart unless-stopped \
      --name "$FRPS_CONT" \
      -p "${FRPS_PORT}:${FRPS_PORT}" \
      -p "${DASH_PORT}:${DASH_PORT}" \
      -v "$FRPS_INI":/etc/frp/frps.ini \
      snowdreamtech/frps:latest >/dev/null
  fi
else
  echo "🐳 Launching frps container..."
  docker run -d --restart unless-stopped \
    --name "$FRPS_CONT" \
    -p "${FRPS_PORT}:${FRPS_PORT}" \
    -p "${DASH_PORT}:${DASH_PORT}" \
    -v "$FRPS_INI":/etc/frp/frps.ini \
    snowdreamtech/frps:latest >/dev/null
fi

# Verify container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${FRPS_CONT}$"; then
  echo "❌ Failed to start frps container. Please check Docker logs."
  exit 1
fi

echo "✅ frps listening on localhost:${FRPS_PORT} (dashboard on port ${DASH_PORT})"

# ---------------------------------------------------------------------------
# 5) Patch Daytona config
# ---------------------------------------------------------------------------
print_header "Configuring Daytona"

echo "🛠️  Patching Daytona config..."
tmp=$(mktemp)
if ! jq --argjson port "$FRPS_PORT" '
  .frps = {"domain":"localhost","port":$port,"protocol":"tcp"}
  | .loginFailExit=false
' "$CONFIG_FILE" > "$tmp"; then
  echo "❌ Failed to patch Daytona config. Please check if jq is installed correctly."
  rm -f "$tmp"
  exit 1
fi

mv "$tmp" "$CONFIG_FILE"
echo "✅ Daytona config updated successfully."

# ---------------------------------------------------------------------------
# 6) Restart Daytona daemon
# ---------------------------------------------------------------------------
print_header "Starting Daytona"

echo "⏹️  Stopping any running Daytona daemon..."
$DAYTONA_BIN server stop 2>/dev/null || true
sleep 2

echo "▶️  Starting Daytona daemon..."
if ! $DAYTONA_BIN server -y; then
  echo "❌ Failed to start Daytona daemon. Please check logs."
  exit 1
fi

# Wait for Daytona to be ready
echo "⏳ Waiting for Daytona to be ready..."
for i in {1..10}; do
  if curl -s http://localhost:3986 >/dev/null; then
    break
  fi
  if [ $i -eq 10 ]; then
    echo "⚠️  Daytona may not be fully ready yet. Please check manually."
  fi
  sleep 2
done

# ---------------------------------------------------------------------------
# 7) Summary
# ---------------------------------------------------------------------------
print_header "Daytona Ready"

echo -e "🎉 Daytona is now running offline at \033[1;32mhttp://localhost:3986\033[0m"
echo ""
echo "📋 Environment variables for your applications:"
echo "   DAYTONA_SERVER_URL=\"http://localhost:3986/api\""
echo "   DAYTONA_TARGET=\"local\""
echo ""
echo "🔗 FRP Dashboard: http://localhost:${DASH_PORT} (admin/admin)"
echo ""
echo "💡 To stop Daytona: $DAYTONA_BIN server stop"
echo "💡 To stop FRP: docker stop $FRPS_CONT"
