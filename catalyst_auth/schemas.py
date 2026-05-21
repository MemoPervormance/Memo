"""Pydantic request/response schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str
    hwid_hash: Optional[str] = None
    cpu_id: Optional[str] = None
    motherboard_serial: Optional[str] = None
    disk_serial: Optional[str] = None
    mac_address: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds


class LicenseActivateRequest(BaseModel):
    license_key: str
    hwid_hash: Optional[str] = None


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    avatar_url: Optional[str]
    is_banned: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    discord_id: Optional[str]
    telegram_id: Optional[str]

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    discord_id: Optional[str] = None
    telegram_id: Optional[str] = None
    notes: Optional[str] = None


class AdminUserUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_banned: Optional[bool] = None
    is_verified: Optional[bool] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# HWID
# ---------------------------------------------------------------------------

class HwidOut(BaseModel):
    id: UUID
    user_id: UUID
    hwid_hash: str
    cpu_id: Optional[str]
    motherboard_serial: Optional[str]
    disk_serial: Optional[str]
    mac_address: Optional[str]
    reset_count: int
    first_bound: datetime
    last_seen: datetime
    last_reset: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


class HwidResetRequest(BaseModel):
    user_id: UUID
    reason: Optional[str] = None


class HwidResetLogOut(BaseModel):
    id: UUID
    user_id: UUID
    reset_by: Optional[UUID]
    old_hwid: Optional[str]
    new_hwid: Optional[str]
    reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# License Keys
# ---------------------------------------------------------------------------

class LicenseKeyOut(BaseModel):
    id: UUID
    license_key: str
    user_id: Optional[UUID]
    plan_type: str
    status: str
    duration_days: Optional[int]
    created_at: datetime
    activated_at: Optional[datetime]
    expires_at: Optional[datetime]
    bound_hwid: Optional[str]
    last_ip: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}


class LicenseCreateRequest(BaseModel):
    plan_type: str   # 1day / 1week / 1month / 3month / 6month / lifetime
    notes: Optional[str] = None
    count: int = Field(default=1, ge=1, le=100)


class LicenseStatusUpdateRequest(BaseModel):
    status: str   # active / expired / banned / paused / unused


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class SubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    license_id: UUID
    subscription_type: Optional[str]
    started_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

class SessionOut(BaseModel):
    id: UUID
    user_id: UUID
    ip_address: Optional[str]
    device_name: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Login Logs
# ---------------------------------------------------------------------------

class LoginLogOut(BaseModel):
    id: UUID
    user_id: UUID
    ip_address: Optional[str]
    user_agent: Optional[str]
    success: bool
    reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# HWID Violations
# ---------------------------------------------------------------------------

class HwidViolationOut(BaseModel):
    id: UUID
    user_id: UUID
    attempted_hwid: Optional[str]
    registered_hwid: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Admin Logs
# ---------------------------------------------------------------------------

class AdminLogOut(BaseModel):
    id: UUID
    admin_id: Optional[UUID]
    action: str
    target_user: Optional[UUID]
    details: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

class AnnouncementOut(BaseModel):
    id: UUID
    title: Optional[str]
    content: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(max_length=255)
    content: str
    is_active: bool = True


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class NotificationOut(BaseModel):
    id: UUID
    user_id: UUID
    title: Optional[str]
    message: Optional[str]
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreateRequest(BaseModel):
    user_id: UUID
    title: str
    message: str


# ---------------------------------------------------------------------------
# API Tokens
# ---------------------------------------------------------------------------

class ApiTokenOut(BaseModel):
    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: Optional[datetime]
    revoked: bool

    model_config = {"from_attributes": True}


class ApiTokenCreated(ApiTokenOut):
    raw_token: str   # only returned once at creation


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

class SettingOut(BaseModel):
    setting_key: str
    setting_value: Optional[str]
    updated_at: datetime

    model_config = {"from_attributes": True}


class SettingUpdateRequest(BaseModel):
    setting_value: str


# ---------------------------------------------------------------------------
# Webhook Logs
# ---------------------------------------------------------------------------

class WebhookLogOut(BaseModel):
    id: UUID
    event_type: Optional[str]
    payload: Optional[str]
    status_code: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
    ok: bool = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list
