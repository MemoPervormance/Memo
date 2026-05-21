"""SQLAlchemy ORM models — mirrors the Catalyst Auth SQL schema 1:1."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, String, Text, DateTime
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username        = Column(String(50), unique=True, nullable=False)
    email           = Column(String(255), unique=True, nullable=False)
    password_hash   = Column(Text, nullable=False)
    role            = Column(String(20), default="user")   # user / admin / owner
    avatar_url      = Column(Text)
    is_banned       = Column(Boolean, default=False)
    is_verified     = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login      = Column(DateTime)
    discord_id      = Column(String(100))
    telegram_id     = Column(String(100))
    notes           = Column(Text)

    hwid_records    = relationship("UserHwid",    back_populates="user", cascade="all, delete-orphan")
    sessions        = relationship("ActiveSession", back_populates="user", cascade="all, delete-orphan")
    notifications   = relationship("Notification",  back_populates="user", cascade="all, delete-orphan")
    subscriptions   = relationship("Subscription",  back_populates="user", cascade="all, delete-orphan")
    login_logs      = relationship("LoginLog",       back_populates="user", cascade="all, delete-orphan")
    api_tokens      = relationship("ApiToken",       back_populates="user", cascade="all, delete-orphan")


class UserHwid(Base):
    __tablename__ = "user_hwid"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    hwid_hash           = Column(Text, nullable=False)
    cpu_id              = Column(Text)
    motherboard_serial  = Column(Text)
    disk_serial         = Column(Text)
    mac_address         = Column(Text)
    reset_count         = Column(Integer, default=0)
    first_bound         = Column(DateTime, default=datetime.utcnow)
    last_seen           = Column(DateTime, default=datetime.utcnow)
    last_reset          = Column(DateTime)
    is_active           = Column(Boolean, default=True)

    user = relationship("User", back_populates="hwid_records")


class HwidResetLog(Base):
    __tablename__ = "hwid_reset_logs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    reset_by   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    old_hwid   = Column(Text)
    new_hwid   = Column(Text)
    reason     = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_key  = Column(String(50), unique=True, nullable=False)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    plan_type    = Column(String(30), nullable=False)
    # 1day / 1week / 1month / 3month / 6month / lifetime
    status       = Column(String(20), default="unused")
    # unused / active / expired / banned / paused
    duration_days = Column(Integer)
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at   = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    expires_at   = Column(DateTime)
    bound_hwid   = Column(Text)
    last_ip      = Column(String(100))
    notes        = Column(Text)

    subscriptions = relationship("Subscription", back_populates="license", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    license_id          = Column(UUID(as_uuid=True), ForeignKey("license_keys.id", ondelete="CASCADE"))
    subscription_type   = Column(String(30))
    started_at          = Column(DateTime, default=datetime.utcnow)
    expires_at          = Column(DateTime)
    is_active           = Column(Boolean, default=True)

    user    = relationship("User",       back_populates="subscriptions")
    license = relationship("LicenseKey", back_populates="subscriptions")


class LoginLog(Base):
    __tablename__ = "login_logs"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    ip_address = Column(String(100))
    user_agent = Column(Text)
    success    = Column(Boolean, default=True)
    reason     = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="login_logs")


class HwidViolation(Base):
    __tablename__ = "hwid_violations"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    attempted_hwid   = Column(Text)
    registered_hwid  = Column(Text)
    ip_address       = Column(String(100))
    created_at       = Column(DateTime, default=datetime.utcnow)


class ActiveSession(Base):
    __tablename__ = "active_sessions"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    session_token = Column(Text, nullable=False)
    ip_address    = Column(String(100))
    device_name   = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)
    expires_at    = Column(DateTime)
    is_active     = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")


class AdminLog(Base):
    __tablename__ = "admin_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action      = Column(Text, nullable=False)
    target_user = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    details     = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title      = Column(String(255))
    content    = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active  = Column(Boolean, default=True)


class Notification(Base):
    __tablename__ = "notifications"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    title      = Column(String(255))
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    revoked    = Column(Boolean, default=False)

    user = relationship("User", back_populates="api_tokens")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    setting_key   = Column(String(100), unique=True)
    setting_value = Column(Text)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type  = Column(String(100))
    payload     = Column(Text)
    status_code = Column(Integer)
    created_at  = Column(DateTime, default=datetime.utcnow)
