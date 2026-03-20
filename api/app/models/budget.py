# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

import uuid
import enum
from sqlalchemy import String, Numeric, Boolean, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class BudgetPeriod(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class Budget(Base, TimestampMixin):
    __tablename__ = "budgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    amount_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    period: Mapped[BudgetPeriod] = mapped_column(nullable=False)
    alert_thresholds: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: [0.8, 1.0]
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
