# MQTT-Alerts

A lightweight MQTT monitoring and Slack alert system for Raspberry Pi 5. Monitors MQTT topics from PLCs and other devices, evaluates messages against configurable rules, and sends Slack notifications via Bot Token API — all managed through a clean web UI. Built for industrial use with AutomationDirect BRX and Productivity PLCs, but works with any MQTT publisher.

## Features

- **Mosquitto MQTT Broker** — pre-configured and managed via systemd
- **Alert Rules** — trigger Slack alerts on contains, regex, JSON path, threshold, or any message
- **Slack Bot Integration** — uses Bot Token API with Block Kit formatting, per-rule channel targeting
- **Web Dashboard** — system health, message stats, recent alerts at a glance
- **Topic Management** — add/remove MQTT topic subscriptions with wildcard support (`+` and `#`)
- **Live Feed** — real-time WebSocket message stream in the browser
- **Message Log** — searchable, paginated history of all MQTT messages
- **Rule Testing** — test rules against sample payloads before enabling
- **Export/Import** — backup and restore alert rules as JSON
- **Auto Cleanup** — configurable data retention (default 7 days messages, 30 days alerts)
- **PLC Ready** — handles null-byte padded payloads, configurable QoS/keepalive, works with AutomationDirect BRX and Productivity PLCs out of the box
- **Security Hardening** — systemd sandboxing with `ProtectSystem=strict`, `NoNewPrivileges`, `PrivateTmp`

## Requirements

- Raspberry Pi 5 with Raspberry Pi OS Bookworm (64-bit)
- Network connection
- A Slack workspace (for alerts — the system works without Slack, logging alerts locally)

## Quick Start

```bash
# Clone the repository
git clone https://github.com/morroware/MQTT-Alerts.git
cd MQTT-Alerts

# Run the installer
sudo bash install.sh
```

The installer is idempotent — safe to re-run for upgrades. It will:

1. Install Mosquitto, Python venv, and required system packages via apt
2. Create a dedicated `mqtt-alerts` system user (no login shell, no home directory)
3. Configure Mosquitto for local network access (TCP :1883 + WebSocket :9001)
4. Set up a Python virtual environment at `/opt/mqtt-alerts/venv` with all dependencies
5. Create the configuration file at `/etc/mqtt-alerts/mqtt-alerts.env` (preserved on re-run)
6. Set proper file ownership and permissions
7. Install, enable, and start three systemd services
8. Print the Web UI URL and next steps

After install, open `http://<your-pi-ip>:8080` in a browser.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Raspberry Pi 5                        │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │  Mosquitto   │   │  Alert       │   │  Web UI    │  │
│  │  MQTT Broker │◄──│  Service     │──►│  (FastAPI) │  │
│  │  (systemd)   │   │  (systemd)   │   │  (systemd) │  │
│  └──────┬───────┘   └──────┬───────┘   └─────┬──────┘  │
│         │                  │                  │         │
│         │ :1883 / :9001   │                  │ :8080   │
│         │                  ▼                  │         │
│         │           ┌──────────┐              │         │
│         │           │  Slack   │              │         │
│         │           │  Bot API │              │         │
│         │           └──────────┘              │         │
└─────────┼─────────────────────────────────────┼─────────┘
          │              LAN                    │
   PLCs / MQTT Clients                    Browser UI
```

### Components

| Component | Description |
|-----------|-------------|
| **Mosquitto** | Industry-standard MQTT broker. Listens on TCP :1883 and WebSocket :9001. Managed by systemd. |
| **Alert Service** (`mqtt-alert-service`) | Python service that subscribes to configured MQTT topics, evaluates messages against rules, and dispatches Slack notifications. |
| **Web UI** (`mqtt-alerts-web`) | FastAPI backend serving a vanilla HTML/CSS/JS SPA. Provides dashboards, rule management, topic browsing, message history, and Slack configuration. |
| **SQLite Database** | Shared between both Python services via WAL mode for safe concurrent access. Stores topics, rules, messages, alert logs, and Slack settings. |

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| MQTT Broker | Mosquitto 2.x | Lightweight, native ARM64 packages in Bookworm repos |
| Alert Service | Python 3.11+ | Ships with Bookworm; rich ecosystem |
| MQTT Client Lib | paho-mqtt 2.x | De-facto standard Python MQTT client |
| Slack Integration | slack-sdk (Bot Token) | Official Slack SDK, `chat.postMessage` API |
| Web Backend | FastAPI + Uvicorn | Async, fast, auto-generated OpenAPI docs |
| Web Frontend | Vanilla HTML/CSS/JS | Zero build step, no Node.js needed |
| Database | SQLite (WAL mode) | Zero-config, file-based, handles concurrent reads |
| ORM | SQLAlchemy 2.x (async) | Async support, mature, well-documented |
| Process Manager | systemd | Native to Bookworm, reliable service management |

**Total Python dependencies:** fastapi, uvicorn, paho-mqtt, slack-sdk, sqlalchemy, aiosqlite, python-dotenv

## Configuration

### Configuration File

The main configuration file is at `/etc/mqtt-alerts/mqtt-alerts.env`. Edit it with:

```bash
sudo nano /etc/mqtt-alerts/mqtt-alerts.env
```

After editing, restart services:

```bash
sudo systemctl restart mqtt-alert-service mqtt-alerts-web
```

### Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MQTT_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` | *(empty)* | MQTT username (leave blank for anonymous) |
| `MQTT_PASSWORD` | *(empty)* | MQTT password |
| `MQTT_CLIENT_ID` | `mqtt-alert-service` | Client ID for the alert service's MQTT connection |
| `MQTT_KEEPALIVE` | `60` | MQTT keepalive interval in seconds |
| `MQTT_CLEAN_SESSION` | `false` | Set to `true` to discard subscriptions/queued messages on reconnect |
| `MQTT_QOS` | `1` | Subscribe QoS level: `0` (at most once), `1` (at least once), `2` (exactly once) |
| `SLACK_BOT_TOKEN` | *(empty)* | Slack bot token (`xoxb-...`). Set via web UI or env file. |
| `SLACK_DEFAULT_CHANNEL` | `#alerts` | Default channel for notifications (overridable per-rule) |
| `SLACK_RATE_LIMIT` | `10` | Maximum Slack alerts per minute (prevents flooding) |
| `DB_PATH` | `/var/lib/mqtt-alerts/alerts.db` | Path to the SQLite database file |
| `WEB_HOST` | `0.0.0.0` | Web UI bind address |
| `WEB_PORT` | `8080` | Web UI port |
| `MESSAGE_RETENTION_DAYS` | `7` | Auto-delete messages older than N days |
| `ALERT_LOG_RETENTION_DAYS` | `30` | Auto-delete alert logs older than N days |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Slack Configuration

The Slack Bot Token can be configured in two ways:

1. **Web UI** (recommended): Go to Settings > Slack Integration and enter your token
2. **Environment file**: Set `SLACK_BOT_TOKEN` in `/etc/mqtt-alerts/mqtt-alerts.env`

When configured via the web UI, the token is stored in the database and takes effect immediately without restarting services.

## Setting Up Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app ("From Scratch")
2. Navigate to **OAuth & Permissions**
3. Add these **Bot Token Scopes**:
   - `chat:write` — send messages
   - `chat:write.public` — post to channels without joining
   - `channels:read` — list available channels
4. Click **Install to Workspace** and authorize
5. Copy the **Bot User OAuth Token** (starts with `xoxb-`)
6. Paste it into the Settings page of the web UI, or set `SLACK_BOT_TOKEN` in the env file

## Services

### Managing Services

```bash
# Check status of all services
sudo systemctl status mosquitto mqtt-alert-service mqtt-alerts-web

# View real-time logs
sudo journalctl -u mqtt-alert-service -f
sudo journalctl -u mqtt-alerts-web -f
sudo journalctl -u mosquitto -f

# Restart services (after config changes)
sudo systemctl restart mqtt-alert-service mqtt-alerts-web

# Stop/start individual services
sudo systemctl stop mqtt-alert-service
sudo systemctl start mqtt-alert-service
```

### Service Details

| Service | Unit Name | Description |
|---------|-----------|-------------|
| Mosquitto | `mosquitto` | MQTT broker on :1883 (TCP) and :9001 (WebSocket) |
| Alert Service | `mqtt-alert-service` | Subscribes to topics, evaluates rules, sends Slack alerts |
| Web UI | `mqtt-alerts-web` | FastAPI server on :8080 serving API and frontend |

All services are configured with `Restart=always` for 24/7 reliability, and include systemd security hardening (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`).

### Health Monitoring

The alert service writes a health file to `/tmp/mqtt-alert-service.health` with JSON status including MQTT connection state. The web dashboard reads this file to display service health.

## Web UI

Access the web UI at `http://<your-pi-ip>:8080`

### Pages

| Page | Description |
|------|-------------|
| **Dashboard** | System health (MQTT connection, alert service status, disk usage), message/alert statistics, recent alerts table |
| **Topics** | Manage MQTT topic subscriptions. Add topics with wildcard support (`+` single-level, `#` multi-level). Enable/disable individual topics. |
| **Rules** | Create and manage alert rules with a visual condition builder. Supports five condition types (see below). Test rules against sample payloads. |
| **Messages** | Searchable, paginated history of all received MQTT messages. Filter by topic or search payload text. Click any row to view full message details. |
| **Live Feed** | Real-time WebSocket stream of MQTT messages. Supports pause/resume, topic filtering, and auto-reconnect. |
| **Settings** | Slack integration configuration (token, channel, rate limit). System health overview. Rule export/import (JSON). |

## Alert Rule Types

| Type | Description | Condition Value | Operator |
|------|-------------|-----------------|----------|
| **Any** | Alert on any message to the matching topic | *(not used)* | *(not used)* |
| **Contains** | Payload contains specific text | Text to search for (e.g., `error`) | *(not used)* |
| **Regex** | Payload matches a regular expression | Regex pattern (e.g., `temp:\s*\d+`) | *(not used)* |
| **JSON Path** | Extract a JSON field and compare its value | `field.path\|target_value` (e.g., `temperature\|30`) | `==`, `!=`, `>`, `<`, `>=`, `<=` |
| **Threshold** | Compare raw numeric payload against a threshold | Numeric value (e.g., `100`) | `==`, `!=`, `>`, `<`, `>=`, `<=` |

### Rule Features

- **Per-rule Slack channel** — override the default channel for specific rules
- **Cooldown** — configurable minimum interval between repeated alerts (prevents alert storms)
- **Custom message templates** — use `{topic}`, `{payload}`, `{rule}`, `{severity}`, `{details}`, `{timestamp}` placeholders
- **Severity levels** — `info`, `warning`, `critical` with color-coded Slack Block Kit messages
- **Rule testing** — test any rule against a sample topic/payload before enabling

## REST API

The REST API is auto-documented at `http://<your-pi-ip>:8080/docs` (Swagger UI) and `http://<your-pi-ip>:8080/redoc` (ReDoc).

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/topics` | List all monitored topics |
| `POST` | `/api/topics` | Add a new topic subscription |
| `GET` | `/api/topics/{id}` | Get a specific topic |
| `PUT` | `/api/topics/{id}` | Update a topic |
| `DELETE` | `/api/topics/{id}` | Delete a topic |
| `GET` | `/api/rules` | List all alert rules |
| `POST` | `/api/rules` | Create a new alert rule |
| `GET` | `/api/rules/{id}` | Get a specific rule |
| `PUT` | `/api/rules/{id}` | Update a rule |
| `DELETE` | `/api/rules/{id}` | Delete a rule |
| `POST` | `/api/rules/{id}/test` | Test a rule against a sample message |
| `GET` | `/api/messages` | Paginated message history (supports `?topic=`, `?search=`, `?limit=`, `?offset=`) |
| `GET` | `/api/messages/topics` | List distinct topics with message counts |
| `WS` | `/api/messages/live` | WebSocket live message stream |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `GET` | `/api/dashboard/recent-alerts` | Recent alert log |
| `GET` | `/api/dashboard/system-health` | System health (service status, MQTT connection, disk usage) |
| `GET` | `/api/settings/slack` | Get Slack configuration |
| `PUT` | `/api/settings/slack` | Update Slack configuration |
| `POST` | `/api/settings/slack/test` | Send a test message to Slack |
| `GET` | `/api/settings/slack/channels` | List Slack channels the bot can access |

## Development

### Prerequisites

- Python 3.11+
- An MQTT broker (Mosquitto) running locally for integration testing

### Running in Development

```bash
# Alert service
cd alert-service
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m mqtt_alerts.main

# Web UI (in a separate terminal)
cd web
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn mqtt_alerts_web.main:app --reload --host 0.0.0.0 --port 8080
```

Then open `http://localhost:8080` in a browser.

For development, both services can share a `.env` file in the project root or `config/mqtt-alerts.env`.

### Running Tests

```bash
# Alert service tests
cd alert-service
pip install -e ".[dev]"
pytest tests/ -v

# Web tests (if present)
cd web
pip install -e ".[dev]"
pytest tests/ -v
```

### Project Structure

```
MQTT-Alerts/
├── CLAUDE.md                    # AI assistant project context
├── README.md                    # This file
├── install.sh                   # One-command production installer
├── uninstall.sh                 # Clean removal script
├── mosquitto/
│   ├── mosquitto.conf           # Broker configuration
│   └── acl.conf                 # Access control list (template)
├── alert-service/
│   ├── pyproject.toml           # Python project metadata & deps
│   ├── mqtt-alert-service.service  # systemd unit file
│   ├── mqtt_alerts/
│   │   ├── __init__.py
│   │   ├── main.py              # Service entry point & main loop
│   │   ├── config.py            # Configuration loader (env / .env)
│   │   ├── database.py          # DB engine & session management
│   │   ├── models.py            # SQLAlchemy models (shared schema)
│   │   ├── mqtt_client.py       # MQTT subscriber & message processor
│   │   ├── rule_engine.py       # Rule evaluation & topic matching
│   │   └── slack_notifier.py    # Slack Bot API dispatcher
│   └── tests/
│       ├── test_rule_engine.py  # Rule engine & topic matching tests
│       └── test_slack_notifier.py  # Slack notifier tests
├── web/
│   ├── pyproject.toml           # Python project metadata & deps
│   ├── mqtt-alerts-web.service  # systemd unit file
│   ├── mqtt_alerts_web/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, lifespan, static serving
│   │   ├── database.py          # DB imports (reuses alert-service models)
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── dashboard.py     # Stats, recent alerts, system health
│   │       ├── topics.py        # Topic CRUD
│   │       ├── rules.py         # Rule CRUD + testing
│   │       ├── messages.py      # Message history, live WebSocket feed
│   │       └── slack.py         # Slack config, test, channel listing
│   └── static/
│       ├── index.html           # SPA shell
│       ├── css/style.css        # All styles (CSS custom properties)
│       └── js/
│           ├── app.js           # SPA router & page controller
│           ├── api.js           # Fetch wrapper & utility functions
│           ├── pages/           # Page modules (dashboard, topics, rules, messages, live, settings)
│           └── components/      # Reusable UI components (toast, modal)
└── config/
    └── mqtt-alerts.example.env  # Example configuration with documentation
```

## Data Management

### Database

The SQLite database is stored at `/var/lib/mqtt-alerts/alerts.db` (configurable via `DB_PATH`). Both the alert service and web UI share this database using WAL (Write-Ahead Logging) mode for safe concurrent access.

### Data Retention

The alert service automatically cleans up old data every hour:

- **Messages**: deleted after `MESSAGE_RETENTION_DAYS` (default: 7 days)
- **Alert logs**: deleted after `ALERT_LOG_RETENTION_DAYS` (default: 30 days)

### Backup

```bash
# Backup the database
sudo cp /var/lib/mqtt-alerts/alerts.db ~/mqtt-alerts-backup.db

# Export rules via the API
curl -s http://localhost:8080/api/rules | python3 -m json.tool > rules-backup.json

# Or use the Export button in Settings > Data Management
```

### Rule Import/Export

Rules can be exported and imported as JSON via the Settings page or the API:

```bash
# Export rules
curl -s http://localhost:8080/api/rules > rules.json

# Import rules (one by one)
curl -X POST http://localhost:8080/api/rules \
  -H "Content-Type: application/json" \
  -d '{"name":"My Rule","topic_pattern":"sensors/#","condition_type":"any","severity":"info"}'
```

## Mosquitto Configuration

The installer replaces the default Mosquitto config at `/etc/mosquitto/mosquitto.conf` (the original is backed up to `mosquitto.conf.bak`) with:

- **TCP listener** on port 1883 (all interfaces)
- **WebSocket listener** on port 9001 (for browser-based MQTT clients)
- **Anonymous access** enabled by default (suitable for trusted local networks)
- **Persistence** enabled at `/var/lib/mosquitto/`
- **Message size limit** of 256KB
- **Max keepalive** set to `0` (accepts any client keepalive value, important for PLCs)
- **Logging** to `/var/log/mosquitto/mosquitto.log`

### Securing Mosquitto

For production deployments on untrusted networks, consider:

1. **Enable authentication**: Create a password file with `mosquitto_passwd` and uncomment `password_file` in the config
2. **Enable ACLs**: Uncomment `acl_file` and configure `acl.conf`
3. **Disable anonymous access**: Set `allow_anonymous false`
4. **Add TLS**: Configure `certfile`, `keyfile`, and `cafile` for encrypted connections
5. **Restrict listeners**: Bind to specific interfaces instead of `0.0.0.0`

## PLC Integration

MQTT-Alerts is designed to work with industrial PLCs that support MQTT, including AutomationDirect BRX and Productivity series controllers. The system handles common PLC payload quirks out of the box.

### How It Works

```
┌──────────────┐     MQTT      ┌──────────────┐     Slack    ┌─────────┐
│  AD PLC      │──────────────►│  MQTT-Alerts │────────────►│  Slack  │
│  (BRX/P2000) │  :1883        │  (Pi 5)      │  Bot API    │  Channel│
└──────────────┘               └──────────────┘              └─────────┘
```

1. Configure your PLC to publish MQTT messages to the Pi's broker on port 1883
2. Add the PLC's topics in the Web UI (Topics page)
3. Create alert rules to match conditions (threshold, contains, JSON path, etc.)
4. Alerts are sent to Slack when rules match

### PLC-Specific Defaults

These defaults are tuned for PLC integration:

| Setting | Default | Why |
|---------|---------|-----|
| `MQTT_QOS` | `1` | At-least-once delivery prevents silent message loss from PLCs |
| `MQTT_CLEAN_SESSION` | `false` | Preserves subscriptions and queued messages across service restarts |
| `max_keepalive` | `0` (unlimited) | Accepts any keepalive value from PLCs without overriding it |
| Null-byte stripping | Automatic | PLCs often pad payloads with `\x00` bytes; these are stripped on receipt |

### Recommended Topic Structure

Organize PLC topics hierarchically for easy wildcard subscriptions:

```
plc/{device_name}/{signal_type}/{signal_name}
```

Examples:
- `plc/brx1/analog/tank_level`
- `plc/brx1/digital/pump_running`
- `plc/brx1/alarm/high_temp`
- `plc/productivity1/status/heartbeat`

Then subscribe with wildcards:
- `plc/brx1/#` — all signals from one PLC
- `plc/+/alarm/#` — all alarms from all PLCs
- `plc/+/analog/tank_level` — tank level from every PLC

### Example Alert Rules for PLCs

**High tank level (threshold):**
- Topic: `plc/brx1/analog/tank_level`
- Type: Threshold
- Operator: `>`
- Value: `85`
- Severity: Warning

**PLC heartbeat lost (any + cooldown):**
- Topic: `plc/brx1/status/heartbeat`
- Type: Any
- Cooldown: 300s (expect heartbeat every 5 min; alert if it stops)

**Fault word contains error (contains):**
- Topic: `plc/brx1/alarm/fault_string`
- Type: Contains
- Value: `FAULT`
- Severity: Critical

**JSON payload from Productivity PLC (json_path):**
- Topic: `plc/productivity1/data`
- Type: JSON Path
- Value: `temperature|150`
- Operator: `>`
- Severity: Critical

### Payload Format Tips

- **Numeric values**: Publish raw numbers (e.g., `75.3`) for threshold rules. Null bytes and whitespace are automatically stripped.
- **String values**: Publish plain text for contains/regex rules. The PLC's string output works as-is.
- **JSON**: If your PLC supports structured output, publish JSON (e.g., `{"temp":72.5,"pressure":14.7}`) and use JSON Path rules for field-level conditions.
- **Retained messages**: Enable retained publish on the PLC so the alert service receives current state after a restart.

### AutomationDirect Setup Notes

**BRX Series:**
- Use the MQTT instruction block in Do-more Designer
- Set the broker IP to the Pi's address, port 1883
- Leave username/password blank (anonymous access is enabled by default)
- Set QoS to 1 for reliable delivery
- Enable retained messages for status/state topics

**Productivity Series:**
- Configure the MQTT client in the hardware configuration
- Point to the Pi's IP on port 1883
- Use the PUBLISH instruction for each data point

### Verifying PLC Connection

```bash
# Watch for messages from the PLC in real time
mosquitto_sub -h localhost -t "plc/#" -v

# Check the alert service logs
sudo journalctl -u mqtt-alert-service -f

# Or use the Live Feed page in the web UI at http://<pi-ip>:8080
```

## Troubleshooting

### Services won't start

```bash
# Check service status and logs
sudo systemctl status mqtt-alert-service
sudo journalctl -u mqtt-alert-service --no-pager -n 50

# Common issues:
# - Missing env file: ensure /etc/mqtt-alerts/mqtt-alerts.env exists
# - Permission errors: run sudo chown -R mqtt-alerts:mqtt-alerts /opt/mqtt-alerts /var/lib/mqtt-alerts
# - Port conflict: check if port 8080 is in use with ss -tlnp | grep 8080
```

### MQTT not connecting

```bash
# Test broker is running
mosquitto_pub -h localhost -t test -m "hello"
mosquitto_sub -h localhost -t test

# Check mosquitto logs
sudo journalctl -u mosquitto -f
```

### PLC messages not arriving

```bash
# Verify Mosquitto is listening and the PLC can reach port 1883
ss -tlnp | grep 1883

# Subscribe to all topics to see what's being published
mosquitto_sub -h localhost -t "#" -v

# Check if the PLC's keepalive is being rejected (look for "exceeded" in logs)
sudo journalctl -u mosquitto -f

# If the PLC connects but messages aren't processed, check the alert service
sudo journalctl -u mqtt-alert-service -f

# Verify your topics are enabled
curl -s http://localhost:8080/api/topics | python3 -m json.tool
```

### Slack alerts not sending

1. Verify the bot token is set (Settings page or env file)
2. Use the "Send Test Message" button in Settings
3. Check the alert service logs: `sudo journalctl -u mqtt-alert-service -f`
4. Ensure bot scopes include `chat:write` and `chat:write.public`
5. Check rate limit — default is 10 alerts/minute

### Database issues

```bash
# Check database file exists and is writable
ls -la /var/lib/mqtt-alerts/alerts.db

# Check WAL mode
sqlite3 /var/lib/mqtt-alerts/alerts.db "PRAGMA journal_mode;"

# Manual cleanup if database grows too large
sqlite3 /var/lib/mqtt-alerts/alerts.db "DELETE FROM messages WHERE received_at < datetime('now', '-3 days');"
sqlite3 /var/lib/mqtt-alerts/alerts.db "VACUUM;"
```

### Web UI not loading

```bash
# Check web service
sudo systemctl status mqtt-alerts-web
sudo journalctl -u mqtt-alerts-web -f

# Test API directly
curl http://localhost:8080/api/dashboard/stats
```

## Uninstall

```bash
sudo bash uninstall.sh
```

The uninstaller will:

1. Stop and disable all MQTT-Alerts services
2. Remove systemd unit files
3. Remove the Mosquitto custom config (Mosquitto itself is left installed)
4. Remove application files from `/opt/mqtt-alerts`
5. Optionally remove the database (`/var/lib/mqtt-alerts`)
6. Optionally remove configuration (`/etc/mqtt-alerts`)
7. Remove the `mqtt-alerts` system user

## Security Notes

- The web UI has **no authentication** by default — it is designed for trusted local networks. If exposing to the internet, put it behind a reverse proxy with authentication (e.g., nginx + basic auth or OAuth).
- The Slack bot token is stored in the database and the env file. The env file is set to `chmod 600` and owned by the service user.
- Both services run as a dedicated non-root user with systemd security hardening.
- Mosquitto allows anonymous connections by default — see [Securing Mosquitto](#securing-mosquitto) above.

## License

MIT
