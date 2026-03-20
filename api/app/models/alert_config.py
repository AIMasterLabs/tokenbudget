# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
import enum
from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class ChannelType(str, enum.Enum):
    slack = "slack"
    webhook = "webhook"
    email = "email"


class AlertConfig(Base, TimestampMixin):
    """User-configured alert delivery channel for a budget."""

    __tablename__ = "alert_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    budget_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False
    )
    channel_type: Mapped[ChannelType] = mapped_column(nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    thresholds: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: [50, 80, 100]
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
