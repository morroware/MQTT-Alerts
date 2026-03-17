"""SQLAlchemy models shared between alert service and web backend."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic_pattern: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    topic_pattern: Mapped[str] = mapped_column(String(512), nullable=False)
    condition_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="any"
    )  # any, contains, regex, json_path, threshold
    condition_value: Mapped[str] = mapped_column(Text, default="")
    condition_operator: Mapped[str] = mapped_column(
        String(10), default="=="
    )  # ==, !=, >, <, >=, <=
    severity: Mapped[str] = mapped_column(
        String(20), default="info"
    )  # info, warning, critical
    slack_channel: Mapped[str] = mapped_column(String(255), default="")
    message_template: Mapped[str] = mapped_column(Text, default="")
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    payload: Mapped[str] = mapped_column(Text, default="")
    qos: Mapped[int] = mapped_column(Integer, default=0)
    retained: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )


class AlertLog(Base):
    __tablename__ = "alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("rules.id"), nullable=False)
    message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("messages.id"), nullable=True
    )
    rule_name: Mapped[str] = mapped_column(String(255), default="")
    topic: Mapped[str] = mapped_column(String(512), default="")
    severity: Mapped[str] = mapped_column(String(20), default="info")
    slack_response: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )


class SlackSettings(Base):
    __tablename__ = "slack_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bot_token: Mapped[str] = mapped_column(Text, default="")
    default_channel: Mapped[str] = mapped_column(String(255), default="#alerts")
    rate_limit: Mapped[int] = mapped_column(Integer, default=10)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
