"""FastAPI application — serves the REST API and static frontend."""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load env
for env_path in [
    Path("/etc/mqtt-alerts/mqtt-alerts.env"),
    Path.home() / ".config" / "mqtt-alerts" / "mqtt-alerts.env",
    Path("config/mqtt-alerts.env"),
    Path(".env"),
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Ensure alert-service is on path for shared models
_alert_service_path = str(Path(__file__).parent.parent.parent / "alert-service")
if _alert_service_path not in sys.path:
    sys.path.insert(0, _alert_service_path)

from .database import close_db, init_db  # noqa: E402
from .routers import dashboard, messages, rules, slack, topics  # noqa: E402

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "/var/lib/mqtt-alerts/alerts.db")
STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Init database
    await init_db(DB_PATH)
    logger.info("Web server starting — DB at %s", DB_PATH)

    # Init Slack notifier for the web layer
    from mqtt_alerts.slack_notifier import SlackNotifier

    notifier = SlackNotifier(
        bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
        default_channel=os.getenv("SLACK_DEFAULT_CHANNEL", "#alerts"),
        rate_limit=int(os.getenv("SLACK_RATE_LIMIT", "10")),
    )
    slack.set_notifier(notifier)

    yield

    await close_db()
    logger.info("Web server stopped")


app = FastAPI(
    title="MQTT-Alerts",
    description="MQTT Monitoring & Slack Alert System",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API routers
app.include_router(dashboard.router)
app.include_router(topics.router)
app.include_router(rules.router)
app.include_router(messages.router)
app.include_router(slack.router)

# Serve static files (CSS, JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "MQTT-Alerts API is running. Static files not found."}


@app.get("/favicon.ico")
async def favicon():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return FileResponse(str(STATIC_DIR / "index.html"), status_code=204)
