#!/usr/bin/env bash
# =============================================================================
# MQTT-Alerts Uninstaller
# Usage: sudo bash uninstall.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[x]${NC} This script must be run as root (use: sudo bash uninstall.sh)"
    exit 1
fi

echo ""
echo "MQTT-Alerts Uninstaller"
echo "======================================"
echo ""

read -p "This will remove MQTT-Alerts services and files. Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Stop and disable services
log "Stopping services..."
systemctl stop mqtt-alert-service 2>/dev/null || true
systemctl stop mqtt-alerts-web 2>/dev/null || true
systemctl disable mqtt-alert-service 2>/dev/null || true
systemctl disable mqtt-alerts-web 2>/dev/null || true

rm -f /etc/systemd/system/mqtt-alert-service.service
rm -f /etc/systemd/system/mqtt-alerts-web.service
systemctl daemon-reload

log "Services removed"

# Remove mosquitto custom config (but don't uninstall mosquitto itself)
rm -f /etc/mosquitto/conf.d/mqtt-alerts.conf
systemctl restart mosquitto 2>/dev/null || true
log "Mosquitto config removed (mosquitto itself left installed)"

# Remove application files
rm -rf /opt/mqtt-alerts
log "Application files removed"

# Ask about data
echo ""
read -p "Remove database and data? ($( echo /var/lib/mqtt-alerts )) [y/N] " remove_data
if [[ "$remove_data" == "y" || "$remove_data" == "Y" ]]; then
    rm -rf /var/lib/mqtt-alerts
    log "Data removed"
else
    warn "Data preserved at /var/lib/mqtt-alerts"
fi

# Ask about config
read -p "Remove configuration? ($( echo /etc/mqtt-alerts )) [y/N] " remove_config
if [[ "$remove_config" == "y" || "$remove_config" == "Y" ]]; then
    rm -rf /etc/mqtt-alerts
    log "Configuration removed"
else
    warn "Configuration preserved at /etc/mqtt-alerts"
fi

# Remove user
if id mqtt-alerts &>/dev/null; then
    userdel mqtt-alerts 2>/dev/null || true
    log "Service user removed"
fi

echo ""
echo "======================================"
echo -e "${GREEN}MQTT-Alerts uninstalled.${NC}"
echo "======================================"
echo ""
