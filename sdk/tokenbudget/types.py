# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget data types."""
from dataclasses import dataclass, field
import time


@dataclass
class UsageEvent:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
    tags: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
