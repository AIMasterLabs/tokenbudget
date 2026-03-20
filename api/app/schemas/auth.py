# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Pydantic schemas for auth endpoints."""
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserInfo(BaseModel):
    id: str
    email: str
    name: str | None
    role: str
    is_active: bool
    department: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserInfo
