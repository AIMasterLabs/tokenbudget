# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class KeyCreate(BaseModel):
    name: str


class KeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KeyCreateResponse(KeyResponse):
    raw_key: str


class KeyRotateResponse(KeyCreateResponse):
    """Response for key rotation: new key details + which old key was revoked."""
    rotated_key_id: uuid.UUID
