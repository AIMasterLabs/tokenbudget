# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Pydantic schemas for groups, group members, project access, and bulk user creation."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


# ── Valid permissions ────────────────────────────────────────────────────────
VALID_PERMISSIONS = {
    "view_analytics",
    "view_costs",
    "view_users",
    "export_reports",
    "manage_keys",
}


# ── Group CRUD ───────────────────────────────────────────────────────────────
class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    name: str | None
    added_at: datetime


class GroupProjectAccessResponse(BaseModel):
    id: str
    project_id: str
    project_name: str | None = None
    permissions: list[str]
    granted_at: datetime


class GroupDetail(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    members: list[GroupMemberResponse]
    project_access: list[GroupProjectAccessResponse]

    model_config = ConfigDict(from_attributes=True)


# ── Group membership ────────────────────────────────────────────────────────
class GroupMemberAdd(BaseModel):
    user_id: str


class GroupMemberBulkAdd(BaseModel):
    user_ids: list[str]


# ── Group project access ────────────────────────────────────────────────────
class GroupProjectAccessCreate(BaseModel):
    project_id: str
    permissions: list[str]

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_PERMISSIONS
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}. Valid: {VALID_PERMISSIONS}")
        if not v:
            raise ValueError("At least one permission is required")
        return v


class GroupProjectAccessUpdate(BaseModel):
    permissions: list[str]

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        invalid = set(v) - VALID_PERMISSIONS
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}. Valid: {VALID_PERMISSIONS}")
        if not v:
            raise ValueError("At least one permission is required")
        return v


# ── Bulk user creation ──────────────────────────────────────────────────────
class BulkUserEntry(BaseModel):
    email: str
    password: str
    name: str
    role: str = "member"
    department: str | None = None
    groups: list[str] = []


class BulkUserCreate(BaseModel):
    users: list[BulkUserEntry]


class BulkUserResultEntry(BaseModel):
    email: str
    id: str | None = None
    ok: bool
    error: str | None = None


class BulkUserCreateResponse(BaseModel):
    created: int
    errors: int
    results: list[BulkUserResultEntry]
