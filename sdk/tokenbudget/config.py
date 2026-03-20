# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget configuration."""
import os


class TokenBudgetConfig:
    """Configuration for the TokenBudget SDK."""

    def __init__(
        self,
        api_key: str = "",
        endpoint: str = "",
        enabled: bool = True,
        flush_interval: float = 1.0,
        max_queue_size: int = 1000,
    ):
        # Resolve api_key: kwarg takes precedence over env var
        resolved_key = api_key or os.environ.get("TOKENBUDGET_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "api_key is required. Pass it as an argument or set the "
                "TOKENBUDGET_API_KEY environment variable."
            )
        self.api_key = resolved_key
        self.endpoint = endpoint or "https://api.tokenbudget.com"
        self.enabled = enabled
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
