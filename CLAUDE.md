# MQTT-Alerts: Raspberry Pi 5 MQTT Monitoring & Slack Alert System

## Project Overview

A production-ready system for Raspberry Pi 5 (Bookworm 64-bit) that runs an MQTT broker, monitors MQTT topics for messages, sends Slack alerts based on configurable rules, and provides a modern web UI for management — all accessible on the local network.

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
│         │ :1883 / :8883   │                  │ :8080   │
│         │                  ▼                  │         │
│         │           ┌──────────┐              │         │
│         │           │  Slack   │              │         │
│         │           │  Webhook │              │         │
│         │           └──────────┘              │         │
└─────────┼─────────────────────────────────────┼─────────┘
          │              LAN                    │
     MQTT Clients                         Browser UI
```

### Components

1. **Mosquitto MQTT Broker** — Industry-standard, lightweight MQTT broker installed via apt and managed by systemd.
2. **Alert Service** (`mqtt-alert-service`) — A Python systemd service that subscribes to configured MQTT topics, evaluates messages against user-defined rules, and dispatches Slack notifications via incoming webhooks.
3. **Web UI** (`mqtt-alerts-web`) — A FastAPI backend serving a React (Vite) frontend. Provides dashboards, rule management, topic browsing, message history, and Slack integration configuration.

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| MQTT Broker | Mosquitto 2.x | Lightweight, native ARM64 packages in Bookworm repos |
| Alert Service | Python 3.11+ | Ships with Bookworm; rich MQTT/Slack library ecosystem |
| MQTT Client Lib | paho-mqtt 2.x | De-facto standard Python MQTT client |
| Slack Integration | slack-sdk (webhook) | Official Slack SDK, simple incoming webhook support |
| Web Backend | FastAPI + Uvicorn | Async, fast, auto-generated OpenAPI docs |
| Web Frontend | React 18 + Vite | Modern, fast builds, excellent DX |
| UI Framework | Tailwind CSS + shadcn/ui | Professional look, accessible components |
| Database | SQLite | Zero-config, file-based, perfect for Pi workloads |
| ORM | SQLAlchemy 2.x | Async support, mature, well-documented |
| Process Manager | systemd | Native to Bookworm, reliable service management |
| Reverse Proxy | Nginx (optional) | Serve frontend static files, proxy API |

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
│   │   ├── config.py          # Configuration loader (env / .env / DB)
│   │   ├── mqtt_client.py     # MQTT subscriber logic
│   │   ├── rule_engine.py     # Message matching & rule evaluation
│   │   ├── slack_notifier.py  # Slack webhook dispatcher
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # DB connection & session management
│   ├── tests/
│   │   ├── test_rule_engine.py
│   │   ├── test_slack_notifier.py
│   │   └── test_mqtt_client.py
│   └── mqtt-alert-service.service  # systemd unit file
│
├── web/
│   ├── backend/
│   │   ├── pyproject.toml
│   │   ├── mqtt_alerts_web/
│   │   │   ├── __init__.py
│   │   │   ├── main.py        # FastAPI app
│   │   │   ├── routers/
│   │   │   │   ├── topics.py      # MQTT topic management
│   │   │   │   ├── rules.py       # Alert rule CRUD
│   │   │   │   ├── messages.py    # Message history & live feed
│   │   │   │   ├── slack.py       # Slack config & test
│   │   │   │   └── dashboard.py   # Dashboard stats
│   │   │   ├── models.py
│   │   │   ├── schemas.py     # Pydantic request/response models
│   │   │   ├── database.py
│   │   │   └── mqtt_bridge.py # Shared MQTT connection for live data
│   │   ├── tests/
│   │   └── mqtt-alerts-web.service  # systemd unit file
│   │
│   └── frontend/
│       ├── package.json
│       ├── vite.config.ts
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       ├── index.html
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── pages/
│           │   ├── Dashboard.tsx       # Overview: active topics, recent alerts, system health
│           │   ├── Topics.tsx          # Browse & subscribe to MQTT topics
│           │   ├── Rules.tsx           # Create/edit/delete alert rules
│           │   ├── MessageLog.tsx      # Searchable message history
│           │   ├── LiveFeed.tsx        # Real-time WebSocket message stream
│           │   └── Settings.tsx        # Slack webhook, broker config, service controls
│           ├── components/
│           │   ├── Layout.tsx
│           │   ├── Sidebar.tsx
│           │   ├── TopicCard.tsx
│           │   ├── RuleForm.tsx
│           │   ├── AlertBadge.tsx
│           │   └── StatusIndicator.tsx
│           ├── hooks/
│           │   ├── useWebSocket.ts
│           │   └── useApi.ts
│           └── lib/
│               └── api.ts             # Typed API client
│
└── config/
    ├── mqtt-alerts.env            # Environment config template
    └── mqtt-alerts.example.env    # Example with documentation
```

---

## Implementation Plan

### Phase 1: Foundation & MQTT Broker Setup

**Goal:** Get Mosquitto running on the Pi with a working configuration.

- [ ] **1.1** Create `mosquitto/mosquitto.conf` with sensible defaults
  - Listener on port 1883 (local network)
  - Optional TLS listener on 8883
  - Logging to `/var/log/mosquitto/`
  - Persistence enabled
  - Allow anonymous for local network (configurable)
- [ ] **1.2** Create `mosquitto/acl.conf` with default access rules
- [ ] **1.3** Write installer section for Mosquitto (`apt install mosquitto mosquitto-clients`)
- [ ] **1.4** Verify broker starts and accepts connections

### Phase 2: Alert Service Core

**Goal:** Python service that subscribes to MQTT topics and sends Slack alerts.

- [ ] **2.1** Set up Python project structure with `pyproject.toml`
  - Dependencies: `paho-mqtt`, `slack-sdk`, `sqlalchemy[asyncio]`, `aiosqlite`, `python-dotenv`
- [ ] **2.2** Implement `config.py` — loads from env vars / `.env` file
  - `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`
  - `SLACK_WEBHOOK_URL`
  - `DB_PATH` (default: `/var/lib/mqtt-alerts/alerts.db`)
  - `LOG_LEVEL`
- [ ] **2.3** Implement `database.py` + `models.py`
  - Tables: `topics`, `rules`, `messages`, `alert_log`, `slack_config`
  - `rules` table: `id`, `name`, `topic_pattern`, `condition_type` (contains, regex, json_path, threshold), `condition_value`, `slack_channel`, `severity`, `enabled`, `cooldown_seconds`
- [ ] **2.4** Implement `mqtt_client.py`
  - Connect to broker with auto-reconnect
  - Subscribe to topics from DB
  - Dispatch incoming messages to rule engine
  - Store messages in DB (with configurable retention)
- [ ] **2.5** Implement `rule_engine.py`
  - Rule types:
    - **Contains** — message payload contains a string
    - **Regex** — payload matches a regex pattern
    - **JSON Path** — extract a JSON field and compare (==, >, <, !=)
    - **Threshold** — numeric value exceeds a threshold
    - **Any** — alert on any message to the topic
  - Cooldown support to prevent alert storms
  - Severity levels: `info`, `warning`, `critical`
- [ ] **2.6** Implement `slack_notifier.py`
  - Format messages with severity-colored attachments
  - Include topic, payload excerpt, timestamp, rule name
  - Rate limiting (max N alerts per minute)
  - Retry with exponential backoff on failures
- [ ] **2.7** Implement `main.py` — service entry point
  - Graceful startup/shutdown
  - Signal handling (SIGTERM, SIGINT)
  - Health check file (`/tmp/mqtt-alert-service.health`)
- [ ] **2.8** Create systemd unit file `mqtt-alert-service.service`
  - `After=mosquitto.service`
  - Restart on failure
  - Runs as dedicated `mqtt-alerts` user
- [ ] **2.9** Write unit tests for rule engine and Slack notifier

### Phase 3: Web Backend (FastAPI)

**Goal:** RESTful API for managing topics, rules, messages, and configuration.

- [ ] **3.1** Set up FastAPI project with `pyproject.toml`
  - Dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `aiosqlite`, `paho-mqtt`, `python-dotenv`, `websockets`
- [ ] **3.2** Implement shared database connection (same SQLite DB as alert service)
- [ ] **3.3** Implement Pydantic schemas for all request/response models
- [ ] **3.4** Implement API routers:
  - `GET/POST /api/topics` — list monitored topics, add new subscriptions
  - `GET/PUT/DELETE /api/topics/{id}` — manage individual topics
  - `GET/POST /api/rules` — list and create alert rules
  - `GET/PUT/DELETE /api/rules/{id}` — manage individual rules
  - `POST /api/rules/{id}/test` — test a rule with sample payload
  - `GET /api/messages` — paginated message history with filters
  - `GET /api/messages/live` — WebSocket endpoint for real-time message stream
  - `GET/PUT /api/settings/slack` — get/update Slack webhook config
  - `POST /api/settings/slack/test` — send test Slack message
  - `GET /api/dashboard/stats` — topic count, message rate, alert counts, uptime
  - `GET /api/dashboard/recent-alerts` — last N alerts with details
  - `GET /api/system/health` — service status, broker connection, disk usage
  - `POST /api/system/restart-service` — restart the alert service
- [ ] **3.5** Implement WebSocket bridge for live MQTT message streaming to browser
- [ ] **3.6** Create systemd unit file `mqtt-alerts-web.service`
- [ ] **3.7** Write API tests

### Phase 4: Web Frontend (React + Vite)

**Goal:** Modern, responsive UI accessible from any device on the local network.

- [ ] **4.1** Scaffold React + Vite + TypeScript project
- [ ] **4.2** Install and configure Tailwind CSS + shadcn/ui components
- [ ] **4.3** Implement layout: sidebar navigation, responsive design
- [ ] **4.4** **Dashboard page**
  - System health status cards (broker, alert service, disk)
  - Active topics count with sparkline
  - Messages per minute chart (last 24h)
  - Recent alerts list with severity badges
  - Quick actions (test Slack, add rule)
- [ ] **4.5** **Topics page**
  - Table of subscribed topics with message counts
  - Add/remove topic subscriptions
  - Topic detail view with recent messages
- [ ] **4.6** **Rules page**
  - Card grid of alert rules with enable/disable toggle
  - Rule creation wizard with condition builder
  - Rule testing with sample payload input
  - Edit and delete functionality
- [ ] **4.7** **Message Log page**
  - Paginated, searchable table of all received messages
  - Filter by topic, date range, content
  - Message detail modal with full payload
- [ ] **4.8** **Live Feed page**
  - Real-time message stream via WebSocket
  - Auto-scroll with pause control
  - Topic filter chips
  - Message highlighting by severity
- [ ] **4.9** **Settings page**
  - Slack webhook URL configuration with test button
  - Broker connection settings display
  - Service status with restart controls
  - Data retention settings
  - Export/import rules as JSON
- [ ] **4.10** Build production assets and configure static file serving

### Phase 5: Installation & Deployment

**Goal:** One-command setup on a fresh Raspberry Pi 5 Bookworm install.

- [ ] **5.1** Create `install.sh`
  - System package installation (mosquitto, python3-venv, node 20 via NodeSource, nginx)
  - Create `mqtt-alerts` system user
  - Set up Python virtual environments for both services
  - Install Python dependencies
  - Build frontend production bundle
  - Copy configuration files
  - Create data directories with proper permissions
  - Enable and start systemd services
  - Print access URL and next steps
- [ ] **5.2** Create `uninstall.sh` — clean removal of all components
- [ ] **5.3** Create `config/mqtt-alerts.example.env` with documented defaults
- [ ] **5.4** Write `README.md` with:
  - Prerequisites
  - Quick start (one-command install)
  - Configuration guide
  - Screenshots
  - Troubleshooting
  - API documentation link (auto-generated at `/api/docs`)

### Phase 6: Polish & Hardening

**Goal:** Production-ready quality.

- [ ] **6.1** Add request validation and error handling throughout
- [ ] **6.2** Implement message retention cleanup (configurable, default 7 days)
- [ ] **6.3** Add basic auth for the web UI (optional, configurable)
- [ ] **6.4** Ensure all services handle Pi restarts gracefully
- [ ] **6.5** Add log rotation configuration
- [ ] **6.6** Performance testing with sustained MQTT message load

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

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_DEFAULT_CHANNEL=      # Optional: override webhook default
SLACK_RATE_LIMIT=10         # Max alerts per minute

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
- **Node version:** 20 LTS (installed via NodeSource for frontend build)
- **Database:** SQLite file shared between alert service and web backend via WAL mode for concurrent reads
- **Service communication:** Both services read/write the same SQLite DB. The alert service watches for rule/topic changes periodically (every 30s) or via an IPC signal.
- **Frontend is built once** during install and served as static files — no Node.js runtime needed in production.

### Running in Development

```bash
# Alert service
cd alert-service
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m mqtt_alerts.main

# Web backend
cd web/backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn mqtt_alerts_web.main:app --reload --port 8080

# Web frontend
cd web/frontend
npm install
npm run dev
```
