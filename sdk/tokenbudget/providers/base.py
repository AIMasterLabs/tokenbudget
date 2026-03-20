# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Abstract base class for LLM provider integrations."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tokenbudget.transport import EventTransport
    from tokenbudget.types import UsageEvent


class BaseProvider(ABC):
    """Abstract LLM provider integration."""

    @abstractmethod
    def detect(self, client: Any) -> bool:
        """Return True if this provider handles the given client."""

    @abstractmethod
    def extract_event(self, response: Any, latency_ms: int) -> "UsageEvent":
        """Extract a UsageEvent from an LLM API response."""

    @abstractmethod
    def patch(self, client: Any, transport: "EventTransport") -> None:
        """Monkey-patch the client to intercept API calls and send events."""
