"""Database connection for the web backend — shares the same SQLite DB as alert service."""

import sys
from pathlib import Path

# Add the alert-service package to the path so we can reuse models
_alert_service_path = str(Path(__file__).parent.parent.parent / "alert-service")
if _alert_service_path not in sys.path:
    sys.path.insert(0, _alert_service_path)

from mqtt_alerts.database import close_db, get_session_factory, init_db  # noqa: E402, F401
from mqtt_alerts.models import AlertLog, Base, Message, Rule, SlackSettings, Topic  # noqa: E402, F401
