# MQTT-Alerts: Raspberry Pi 5 MQTT Monitoring & Slack Alert System

## Project Overview

A production-ready system for Raspberry Pi 5 (Bookworm 64-bit) that runs an MQTT broker, monitors MQTT topics for messages, sends Slack alerts based on configurable rules, and provides a modern web UI for management — all accessible on the local network.

**Design philosophy:** Minimal dependencies, no build tools, no Node.js. Pure Python backend with vanilla HTML/CSS/JavaScript frontend. Runs entirely on packages available in Bookworm repos + a small Python venv.

---

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
     MQTT Clients                         Browser UI
```

### Components

1. **Mosquitto MQTT Broker** — Industry-standard, lightweight MQTT broker installed via apt and managed by systemd.
2. **Alert Service** (`mqtt-alert-service`) — A Python systemd service that subscribes to configured MQTT topics, evaluates messages against user-defined rules, and dispatches Slack notifications via a Slack Bot Token (`chat.postMessage` API).
3. **Web UI** (`mqtt-alerts-web`) — A FastAPI backend serving vanilla HTML/CSS/JS static files. Provides dashboards, rule management, topic browsing, message history, and Slack integration configuration. Zero build step.

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| MQTT Broker | Mosquitto 2.x | Lightweight, native ARM64 packages in Bookworm repos |
| Alert Service | Python 3.11+ | Ships with Bookworm; rich MQTT/Slack library ecosystem |
| MQTT Client Lib | paho-mqtt 2.x | De-facto standard Python MQTT client |
| Slack Integration | slack-sdk (Bot Token) | Official Slack SDK, `chat.postMessage` API via Bot Token |
| Web Backend | FastAPI + Uvicorn | Async, fast, auto-generated OpenAPI docs |
| Web Frontend | Vanilla HTML/CSS/JS | Zero build step, no Node.js, minimal complexity |
| Database | SQLite (WAL mode) | Zero-config, file-based, perfect for Pi workloads |
| ORM | SQLAlchemy 2.x (async) | Async support, mature, well-documented |
| Process Manager | systemd | Native to Bookworm, reliable service management |

**Total Python dependencies:** fastapi, uvicorn, paho-mqtt, slack-sdk, sqlalchemy, aiosqlite, python-dotenv

---

## Directory Structure

```
MQTT-Alerts/
├── CLAUDE.md                  # This file — project plan & dev guide
├── README.md                  # User-facing documentation
├── install.sh                 # One-command installer for the Pi
├── uninstall.sh               # Clean removal script
│
├── mosquitto/
│   ├── mosquitto.conf         # Broker configuration
│   └── acl.conf               # Access control list (optional)
│
├── alert-service/
│   ├── pyproject.toml         # Python project metadata & deps
│   ├── mqtt_alerts/
│   │   ├── __init__.py
│   │   ├── main.py            # Service entry point
│   │   ├── config.py          # Configuration loader (env / .env)
│   │   ├── mqtt_client.py     # MQTT subscriber logic
│   │   ├── rule_engine.py     # Message matching & rule evaluation
│   │   ├── slack_notifier.py  # Slack Bot API dispatcher
│   │   ├── models.py          # SQLAlchemy models (shared schema)
│   │   └── database.py        # DB connection & session management
│   ├── tests/
│   │   ├── test_rule_engine.py
│   │   └── test_slack_notifier.py
│   └── mqtt-alert-service.service  # systemd unit file
│
├── web/
│   ├── pyproject.toml         # Python project metadata & deps
│   ├── mqtt_alerts_web/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app + static file serving
│   │   ├── database.py        # Shared DB connection
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── topics.py      # MQTT topic management
│   │       ├── rules.py       # Alert rule CRUD
│   │       ├── messages.py    # Message history & live feed
│   │       ├── slack.py       # Slack config & test
│   │       └── dashboard.py   # Dashboard stats & system health
│   ├── static/                # Vanilla frontend — served directly
│   │   ├── index.html
│   │   ├── css/
│   │   │   └── style.css      # All styles — CSS custom properties, no framework
│   │   └── js/
│   │       ├── app.js         # SPA router & page loader
│   │       ├── api.js         # Fetch wrapper for backend API
│   │       ├── pages/
│   │       │   ├── dashboard.js
│   │       │   ├── topics.js
│   │       │   ├── rules.js
│   │       │   ├── messages.js
│   │       │   ├── live.js
│   │       │   └── settings.js
│   │       └── components/
│   │           ├── toast.js
│   │           └── modal.js
│   ├── tests/
│   └── mqtt-alerts-web.service    # systemd unit file
│
└── config/
    ├── mqtt-alerts.env            # Live config (created by installer)
    └── mqtt-alerts.example.env    # Example with documentation
```

---

## Data Models

### Topics Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| topic_pattern | TEXT UNIQUE | MQTT topic (supports wildcards: +, #) |
| description | TEXT | User-friendly description |
| enabled | BOOLEAN | Whether actively subscribed |
| created_at | DATETIME | When added |

### Rules Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Human-readable rule name |
| topic_pattern | TEXT | MQTT topic pattern to match |
| condition_type | TEXT | contains, regex, json_path, threshold, any |
| condition_value | TEXT | The value/pattern to match against |
| condition_operator | TEXT | For json_path/threshold: ==, !=, >, <, >=, <= |
| severity | TEXT | info, warning, critical |
| slack_channel | TEXT | Override default channel (optional) |
| message_template | TEXT | Custom Slack message template (optional) |
| cooldown_seconds | INTEGER | Min seconds between repeated alerts |
| enabled | BOOLEAN | Whether rule is active |
| created_at | DATETIME | When created |
| last_triggered | DATETIME | When rule last fired |

### Messages Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| topic | TEXT | MQTT topic |
| payload | TEXT | Message payload |
| qos | INTEGER | MQTT QoS level |
| retained | BOOLEAN | Whether message was retained |
| received_at | DATETIME | When received |

### Alert Log Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| rule_id | INTEGER FK | Rule that triggered |
| message_id | INTEGER FK | Message that triggered it |
| severity | TEXT | Alert severity |
| slack_response | TEXT | Slack API response status |
| sent_at | DATETIME | When alert was sent |

---

## Configuration Reference

```env
# MQTT Broker
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=              # Leave blank for anonymous
MQTT_PASSWORD=
MQTT_CLIENT_ID=mqtt-alert-service

# Slack Bot Token (create at https://api.slack.com/apps)
# Required bot scopes: chat:write, chat:write.public, channels:read
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_DEFAULT_CHANNEL=#alerts   # Default channel for notifications
SLACK_RATE_LIMIT=10             # Max alerts per minute

# Database
DB_PATH=/var/lib/mqtt-alerts/alerts.db

# Web UI
WEB_HOST=0.0.0.0
WEB_PORT=8080

# Retention
MESSAGE_RETENTION_DAYS=7
ALERT_LOG_RETENTION_DAYS=30

# Logging
LOG_LEVEL=INFO
```

---

## Development Notes

- **Python version:** 3.11+ (ships with Bookworm)
- **No Node.js required** — frontend is vanilla HTML/CSS/JS with no build step
- **Database:** SQLite file shared between alert service and web backend via WAL mode for concurrent reads
- **Service communication:** Both services read/write the same SQLite DB. The alert service watches for rule/topic changes periodically (every 30s).
- **Single venv** can be used for both services in production (shared deps).

### Running in Development

```bash
# Alert service
cd alert-service
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m mqtt_alerts.main

# Web (backend + static frontend served together)
cd web
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn mqtt_alerts_web.main:app --reload --host 0.0.0.0 --port 8080
# Then open http://<pi-ip>:8080 in a browser
```
