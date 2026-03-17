# MQTT-Alerts

A lightweight MQTT monitoring and Slack alert system for Raspberry Pi 5. Monitors MQTT topics, evaluates messages against configurable rules, and sends Slack notifications via Bot Token API — all managed through a clean web UI.

## Features

- **Mosquitto MQTT Broker** — pre-configured and managed via systemd
- **Alert Rules** — trigger Slack alerts on contains, regex, JSON path, threshold, or any message
- **Slack Bot Integration** — uses Bot Token API with Block Kit formatting, per-rule channel targeting
- **Web Dashboard** — system health, message stats, recent alerts at a glance
- **Topic Management** — add/remove MQTT topic subscriptions with wildcard support
- **Live Feed** — real-time WebSocket message stream in the browser
- **Message Log** — searchable, paginated history of all MQTT messages
- **Rule Testing** — test rules against sample payloads before enabling
- **Export/Import** — backup and restore alert rules as JSON
- **Auto Cleanup** — configurable data retention (default 7 days messages, 30 days alerts)

## Requirements

- Raspberry Pi 5 with Raspberry Pi OS Bookworm (64-bit)
- Network connection
- A Slack workspace (for alerts)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/morroware/MQTT-Alerts.git
cd MQTT-Alerts

# Run the installer
sudo bash install.sh
```

The installer will:
1. Install Mosquitto, Python venv, and required system packages
2. Create a dedicated `mqtt-alerts` system user
3. Set up a Python virtual environment with all dependencies
4. Configure Mosquitto for local network access
5. Install and start three systemd services
6. Print the Web UI URL and next steps

## Configuration

Edit `/etc/mqtt-alerts/mqtt-alerts.env`:

```bash
sudo nano /etc/mqtt-alerts/mqtt-alerts.env
```

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | *(empty)* | Your Slack bot token (xoxb-...) |
| `SLACK_DEFAULT_CHANNEL` | `#alerts` | Default channel for notifications |
| `MQTT_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `WEB_PORT` | `8080` | Web UI port |
| `MESSAGE_RETENTION_DAYS` | `7` | Auto-delete messages older than N days |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

After editing, restart services:

```bash
sudo systemctl restart mqtt-alert-service mqtt-alerts-web
```

## Setting Up Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app
2. Navigate to **OAuth & Permissions**
3. Add these **Bot Token Scopes**:
   - `chat:write` — send messages
   - `chat:write.public` — post to channels without joining
   - `channels:read` — list available channels
4. Click **Install to Workspace** and authorize
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
6. Paste it into the Settings page of the web UI, or set `SLACK_BOT_TOKEN` in the env file

## Services

```bash
# Check status
sudo systemctl status mosquitto
sudo systemctl status mqtt-alert-service
sudo systemctl status mqtt-alerts-web

# View logs
sudo journalctl -u mqtt-alert-service -f
sudo journalctl -u mqtt-alerts-web -f

# Restart
sudo systemctl restart mqtt-alert-service mqtt-alerts-web
```

## Web UI

Access the web UI at `http://<your-pi-ip>:8080`

Pages:
- **Dashboard** — system health, message stats, recent alerts
- **Topics** — manage MQTT topic subscriptions
- **Rules** — create and manage alert rules with condition builder
- **Messages** — searchable message history
- **Live Feed** — real-time WebSocket message stream
- **Settings** — Slack configuration, system health, data export/import

## API

The REST API is auto-documented at `http://<your-pi-ip>:8080/docs` (Swagger UI).

Key endpoints:
- `GET /api/topics` — list monitored topics
- `GET /api/rules` — list alert rules
- `GET /api/messages` — paginated message history
- `GET /api/dashboard/stats` — dashboard statistics
- `GET /api/dashboard/system-health` — system health check
- `WS /api/messages/live` — WebSocket live message stream

## Alert Rule Types

| Type | Description | Example |
|------|-------------|---------|
| **Any** | Alert on any message to the topic | Topic: `alerts/#` |
| **Contains** | Payload contains specific text | Value: `error` |
| **Regex** | Payload matches a regular expression | Value: `temp:\s*\d+` |
| **JSON Path** | Extract JSON field and compare | Value: `temperature\|30`, Operator: `>` |
| **Threshold** | Raw numeric payload vs threshold | Value: `100`, Operator: `>=` |

## Architecture

```
Mosquitto (:1883) <── Alert Service (Python) ──> Slack Bot API
                          │
                     SQLite DB (WAL)
                          │
                   FastAPI Web UI (:8080) ──> Browser
```

- **Zero build step** — vanilla HTML/CSS/JS frontend, no Node.js
- **Minimal dependencies** — Python 3.11+, 7 pip packages, apt packages
- **Shared database** — both services use the same SQLite DB with WAL mode
- **systemd managed** — auto-restart, logging, security hardening

## Uninstall

```bash
sudo bash uninstall.sh
```

## License

MIT
