#!/usr/bin/env bash
# -----------------------------------------------------------------------------
#  setup_daytona_local.sh  —  one-time Daytona bootstrap for local development
# -----------------------------------------------------------------------------
#  • Works on macOS (Intel/ARM) and Linux
#  • Downloads and installs Daytona CLI
#  • Creates necessary directories and configuration
#  • Sets up aliases for Daytona commands
#  • Prepares environment for start-daytona-local.sh
#  • Registers Suna AgentDocker image with Daytona
# -----------------------------------------------------------------------------
set -euo pipefail
IFS=$'\n\t'

# ---------- Constants --------------------------------------------------------
PERSONAL_BIN="${PERSONAL_BIN:-$HOME/personal/bin}"
DAYTONA_HOME="${DAYTONA_HOME:-$PERSONAL_BIN}"
DAYTONA_BIN="${DAYTONA_BIN:-$DAYTONA_HOME/daytona}"
FRP_HOME="$PERSONAL_BIN/frp"
FRPS_INI="$FRP_HOME/frps.ini"

CONFIG_MACOS="$HOME/Library/Application Support/daytona/server/config.json"
CONFIG_LINUX="$HOME/.config/daytona/server/config.json"
CONFIG_FILE=""

# ---------- Helper Functions -------------------------------------------------
print_header() {
  echo -e "\n\033[1;36m$1\033[0m"
  echo -e "\033[1;36m${1//?/=}\033[0m"
}

# ---------- Sanity Checks ----------------------------------------------------
print_header "Checking Prerequisites"

# Check for required commands
command -v docker >/dev/null 2>&1 || { echo "❌ Docker Desktop required."; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ jq required (brew install jq)."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "❌ curl required."; exit 1; }

# Check Docker is running
if ! docker info &> /dev/null; then
  echo "❌ Docker is not running. Please start Docker first."
  exit 1
fi

echo "✅ All prerequisites are met."

# ---------- Create Directories -----------------------------------------------
print_header "Creating Directories"

# Create personal bin directory if it doesn't exist
if [ ! -d "$PERSONAL_BIN" ]; then
  echo "📁 Creating directory: $PERSONAL_BIN"
  mkdir -p "$PERSONAL_BIN"
fi

# Create FRP directory if it doesn't exist
if [ ! -d "$FRP_HOME" ]; then
  echo "📁 Creating directory: $FRP_HOME"
  mkdir -p "$FRP_HOME"
fi

echo "✅ Directories created."

# ---------- Install / Update Daytona ----------------------------------------
print_header "Installing Daytona CLI"

# Determine OS and architecture
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

# Map architecture to Daytona's naming
if [ "$ARCH" = "x86_64" ]; then
  DAYTONA_ARCH="amd64"
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
  DAYTONA_ARCH="arm64"
else
  echo "❌ Unsupported architecture: $ARCH"
  exit 1
fi

# Check if Daytona is already installed
if [[ -x "$DAYTONA_BIN" ]]; then
  echo "🔎 Daytona binary already present at $DAYTONA_BIN"
else
  # Download URL - use latest release
  DAYTONA_URL="https://github.com/daytonaio/daytona/releases/latest/download/daytona_${OS}_${DAYTONA_ARCH}.tar.gz"
  
  echo "⬇️ Downloading Daytona CLI from $DAYTONA_URL"
  curl -L "$DAYTONA_URL" | tar xz -C "$PERSONAL_BIN"
  chmod +x "$DAYTONA_BIN"
  echo "✅ Daytona installed to $DAYTONA_BIN"
fi

# ---------- Add Alias to Shell RC --------------------------------------------
print_header "Setting Up Aliases"

# Determine shell configuration file
SHELL_RC=${SHELL##*/}   # zsh or bash
if [[ "$SHELL_RC" == "zsh" ]]; then
  RC_FILE="$HOME/.zshrc"
elif [[ "$SHELL_RC" == "bash" ]]; then
  if [[ -f "$HOME/.bash_profile" ]]; then
    RC_FILE="$HOME/.bash_profile"
  else
    RC_FILE="$HOME/.bashrc"
  fi
else
  echo "⚠️ Could not determine shell configuration file. Please add aliases manually."
  RC_FILE=""
fi

if [ -n "$RC_FILE" ]; then
  # Check if aliases already exist
  if ! grep -q "alias daytona=" "$RC_FILE"; then
    echo "📝 Adding Daytona aliases to $RC_FILE"
    cat >> "$RC_FILE" << EOF

# Daytona aliases
alias daytona="$DAYTONA_BIN"
alias daytona-start="$PERSONAL_BIN/start-daytona-local.sh"
EOF
    echo "✅ Aliases added to $RC_FILE"
    echo "   Please run 'source $RC_FILE' to apply changes."
  else
    echo "✅ Daytona aliases already exist in $RC_FILE"
  fi
fi

# ---------- Generate Default Config If Missing -------------------------------
if [[ ! -f "$CONFIG_MACOS" && ! -f "$CONFIG_LINUX" ]]; then
  print_header "Generating Default Configuration"
  
  echo "⚙️ Generating default Daytona config (30-second dry run)…"
  "$DAYTONA_BIN" serve &  # start in bg
  DAYTONA_PID=$!
  sleep 5                  # wait for config to be written
  kill "$DAYTONA_PID" 2>/dev/null || true
  
  echo "✅ Default configuration generated."
fi

# ---------- Backup Vanilla Config -------------------------------------------
print_header "Backing Up Configuration"

CONFIG_FILE=""
[[ -f "$CONFIG_MACOS" ]] && CONFIG_FILE="$CONFIG_MACOS"
[[ -f "$CONFIG_LINUX" ]] && CONFIG_FILE="$CONFIG_LINUX"

if [[ -n "$CONFIG_FILE" ]]; then
  BACKUP_FILE="${CONFIG_FILE}.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CONFIG_FILE" "$BACKUP_FILE"
  echo "💾 Original config backed up to $BACKUP_FILE"
else
  echo "⚠️ Could not locate config.json — something's off."
  exit 1
fi

# ---------- Create FRP Configuration -----------------------------------------
print_header "Creating FRP Configuration"

# Create frps.ini
cat > "$FRP_HOME/frps.ini" << EOF
[common]
bind_port = 7000
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = admin
EOF

echo "✅ FRP configuration created at $FRP_HOME/frps.ini"

# ---------- Create start-daytona-local.sh -----------------------------------
print_header "Creating start-daytona-local.sh"

cat > "$PERSONAL_BIN/start-daytona-local.sh" << 'EOF'
#!/usr/bin/env bash
# ---------------------------------------------------------------------------
#  start-daytona-local.sh  —  Offline Daytona + frps one-liner
# ---------------------------------------------------------------------------
#  • Works on macOS and Linux with Docker running
#  • Creates/uses  $PERSONAL_BIN/frp  for config + Docker volume
#  • Patches Daytona server config.json
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
# 2) Preconditions
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 3) Start frps container
# ---------------------------------------------------------------------------
echo "🔄 Checking frps container status..."
if docker ps -a --format '{{.Names}}' | grep -q "^${FRPS_CONT}$"; then
  echo "🐳 Restarting frps container …"
  docker restart "$FRPS_CONT" >/dev/null
else
  echo "🐳 Launching frps container …"
  docker run -d --restart unless-stopped \
    --name "$FRPS_CONT" \
    -p "${FRPS_PORT}:${FRPS_PORT}" \
    -p "${DASH_PORT}:${DASH_PORT}" \
    -v "$FRPS_INI":/etc/frp/frps.ini \
    snowdreamtech/frps:latest >/dev/null
fi
echo "✅ frps listening on localhost:${FRPS_PORT}"

# ---------------------------------------------------------------------------
# 4) Patch Daytona config
# ---------------------------------------------------------------------------
echo "🛠️ Patching Daytona config …"
tmp=$(mktemp)
jq --argjson port "$FRPS_PORT" '
  .frps = {"domain":"localhost","port":$port,"protocol":"tcp"}
  | .loginFailExit=false
' "$CONFIG_FILE" > "$tmp" && mv "$tmp" "$CONFIG_FILE"

# ---------------------------------------------------------------------------
# 5) Restart Daytona daemon
# ---------------------------------------------------------------------------
echo "⏹️ Stopping any running Daytona daemon …"
$DAYTONA_BIN server stop 2>/dev/null || true

echo "▶️ Starting Daytona daemon …"
$DAYTONA_BIN server -y

echo -e "\n🎉 Daytona is now running offline at http://localhost:3986"
echo "   Remember to set in your apps:"
echo "     DAYTONA_SERVER_URL=\"http://localhost:3986/api\""
echo "     DAYTONA_TARGET=\"local\""
EOF

chmod +x "$PERSONAL_BIN/start-daytona-local.sh"
echo "✅ start-daytona-local.sh created at $PERSONAL_BIN/start-daytona-local.sh"

# ---------- Register AgentDocker Image --------------------------------------
print_header "Registering AgentDocker Image"

# Start Daytona server if not running (needed for image registration)
echo "🔄 Ensuring Daytona server is running..."
if ! "$DAYTONA_BIN" server status &>/dev/null; then
  echo "▶️ Starting Daytona server..."
  "$DAYTONA_BIN" server -y &
  # Wait for server to start
  sleep 5
  STARTED_SERVER=true
else
  echo "✅ Daytona server is already running"
  STARTED_SERVER=false
fi

# Register the Suna AgentDocker image
echo "🐳 Registering Suna AgentDocker image with Daytona..."
if "$DAYTONA_BIN" image add \
  --name "kortix/suna:0.1.2" \
  --entrypoint "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"; then
  echo "✅ AgentDocker image registered successfully"
else
  echo "⚠️ Failed to register AgentDocker image. You may need to register it manually:"
  echo "   daytona image add --name \"kortix/suna:0.1.2\" --entrypoint \"/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf\""
fi

# Stop the server if we started it
if [ "$STARTED_SERVER" = true ]; then
  echo "⏹️ Stopping temporary Daytona server..."
  "$DAYTONA_BIN" server stop
fi

# ---------- Summary ---------------------------------------------------------
print_header "Setup Complete"

echo "✅ Daytona CLI installed at: $DAYTONA_BIN"
echo "✅ FRP configuration created at: $FRP_HOME/frps.ini"
echo "✅ start-daytona-local.sh created at: $PERSONAL_BIN/start-daytona-local.sh"
echo "✅ Suna AgentDocker image registered with Daytona"
if [ -n "${RC_FILE:-}" ]; then
  echo "✅ Aliases added to: $RC_FILE"
fi

echo -e "\n🚀 Next Steps:"
if [ -n "${RC_FILE:-}" ]; then
  echo "1. Run 'source $RC_FILE' to load the aliases"
  echo "2. Start Daytona with: daytona-start"
else
  echo "1. Start Daytona with: $PERSONAL_BIN/start-daytona-local.sh"
fi
echo "3. Use the Suna AI start script: ./start-suna-local.sh"
echo ""
echo "🔗 Daytona will be available at: http://localhost:3986"
