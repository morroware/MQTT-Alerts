#!/usr/bin/env bash
# =============================================================================
# MQTT-Alerts Installer
# One-command setup for Raspberry Pi 5 (Bookworm 64-bit)
# Usage: sudo bash install.sh
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/mqtt-alerts"
DATA_DIR="/var/lib/mqtt-alerts"
CONFIG_DIR="/etc/mqtt-alerts"
SERVICE_USER="mqtt-alerts"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[x]${NC} $1"; exit 1; }

# ---- Preflight checks ----

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use: sudo bash install.sh)"
fi

log "MQTT-Alerts Installer"
echo "======================================"
echo ""

# ---- Step 1: System packages ----

log "Installing system packages..."
apt-get update -qq
apt-get install -y -qq mosquitto mosquitto-clients python3-venv python3-pip > /dev/null 2>&1
log "System packages installed"

# ---- Step 2: Create service user ----

if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$SERVICE_USER"
    log "Created system user: $SERVICE_USER"
else
    log "User $SERVICE_USER already exists"
fi

# ---- Step 3: Create directories ----

mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$CONFIG_DIR"
chown "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
log "Created directories"

# ---- Step 4: Copy project files ----

log "Installing application files..."
cp -r "$SCRIPT_DIR/alert-service" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/web" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/mosquitto" "$INSTALL_DIR/"

# ---- Step 5: Configure Mosquitto ----

log "Configuring Mosquitto..."
cp "$INSTALL_DIR/mosquitto/mosquitto.conf" /etc/mosquitto/conf.d/mqtt-alerts.conf

# Restart mosquitto to pick up new config
systemctl restart mosquitto
systemctl enable mosquitto
log "Mosquitto configured and running"

# ---- Step 6: Python virtual environment ----

log "Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# Install alert service
pip install --quiet "$INSTALL_DIR/alert-service"

# Install web backend
pip install --quiet "$INSTALL_DIR/web"

deactivate
log "Python packages installed"

# ---- Step 7: Configuration ----

if [[ ! -f "$CONFIG_DIR/mqtt-alerts.env" ]]; then
    cp "$SCRIPT_DIR/config/mqtt-alerts.example.env" "$CONFIG_DIR/mqtt-alerts.env"
    chmod 600 "$CONFIG_DIR/mqtt-alerts.env"
    chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/mqtt-alerts.env"
    log "Configuration file created at $CONFIG_DIR/mqtt-alerts.env"
    warn "Edit $CONFIG_DIR/mqtt-alerts.env to set your Slack bot token"
else
    log "Configuration file already exists, not overwriting"
fi

# ---- Step 8: Install systemd services ----

log "Installing systemd services..."

cp "$INSTALL_DIR/alert-service/mqtt-alert-service.service" /etc/systemd/system/
cp "$INSTALL_DIR/web/mqtt-alerts-web.service" /etc/systemd/system/

systemctl daemon-reload

systemctl enable mqtt-alert-service
systemctl enable mqtt-alerts-web

systemctl start mqtt-alert-service
systemctl start mqtt-alerts-web

log "Services installed and started"

# ---- Step 9: Set permissions ----

chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"

# ---- Done ----

echo ""
echo "======================================"
echo -e "${GREEN}MQTT-Alerts installed successfully!${NC}"
echo "======================================"
echo ""

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo -e "  Web UI:     ${BLUE}http://${IP}:8080${NC}"
echo -e "  MQTT Broker: ${BLUE}${IP}:1883${NC}"
echo -e "  API Docs:   ${BLUE}http://${IP}:8080/docs${NC}"
echo ""
echo "  Configuration: $CONFIG_DIR/mqtt-alerts.env"
echo "  Database:      $DATA_DIR/alerts.db"
echo ""
echo "  Services:"
echo "    systemctl status mqtt-alert-service"
echo "    systemctl status mqtt-alerts-web"
echo "    systemctl status mosquitto"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Edit $CONFIG_DIR/mqtt-alerts.env"
echo "  2. Set your SLACK_BOT_TOKEN (create app at https://api.slack.com/apps)"
echo "  3. Restart services: sudo systemctl restart mqtt-alert-service mqtt-alerts-web"
echo "  4. Open the Web UI and add topics + rules"
echo ""
