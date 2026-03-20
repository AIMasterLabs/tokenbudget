# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
PriceChange model — tracks detected AI model pricing changes.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PriceChange(Base):
    __tablename__ = "price_changes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    old_input_price: Mapped[float] = mapped_column(Float, nullable=False)
    new_input_price: Mapped[float] = mapped_column(Float, nullable=False)
    old_output_price: Mapped[float] = mapped_column(Float, nullable=False)
    new_output_price: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    notified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
