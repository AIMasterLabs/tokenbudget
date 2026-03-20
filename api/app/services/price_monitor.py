# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Price change detection and notification formatting.

Compares pricing dictionaries, persists changes, and formats
notification messages for email and Slack.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_change import PriceChange

logger = logging.getLogger(__name__)

# Provider prefix mapping for display purposes
_PROVIDER_PREFIXES: dict[str, str] = {
    "gpt-": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "text-embedding-": "openai",
    "claude-": "anthropic",
}


def _infer_provider(model: str) -> str:
    """Infer the provider name from a model string."""
    for prefix, provider in _PROVIDER_PREFIXES.items():
        if model.startswith(prefix):
            return provider
    return "unknown"


def _pct_change(old: float, new: float) -> float:
    """Return percentage change from old to new. Returns 0 if old is 0."""
    if old == 0:
        return 100.0 if new > 0 else 0.0
    return round(((new - old) / old) * 100, 2)


def detect_price_changes(
    old_prices: dict[str, tuple[float, float]],
    new_prices: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    """
    Compare two pricing dicts and return a list of changes.

    Each dict maps model name -> (input_per_1k, output_per_1k).
    Returns list of dicts with keys:
        provider, model, old_input_price, new_input_price,
        old_output_price, new_output_price
    """
    changes: list[dict[str, Any]] = []

    all_models = set(old_prices.keys()) | set(new_prices.keys())

    for model in sorted(all_models):
        old_input, old_output = old_prices.get(model, (0.0, 0.0))
        new_input, new_output = new_prices.get(model, (0.0, 0.0))

        if old_input != new_input or old_output != new_output:
            changes.append({
                "provider": _infer_provider(model),
                "model": model,
                "old_input_price": old_input,
                "new_input_price": new_input,
                "old_output_price": old_output,
                "new_output_price": new_output,
            })

    return changes


async def store_price_changes(
    changes: list[dict[str, Any]],
    db: AsyncSession,
) -> list[PriceChange]:
    """Persist detected price changes to the database."""
    records: list[PriceChange] = []
    now = datetime.now(timezone.utc)

    for change in changes:
        record = PriceChange(
            provider=change["provider"],
            model=change["model"],
            old_input_price=change["old_input_price"],
            new_input_price=change["new_input_price"],
            old_output_price=change["old_output_price"],
            new_output_price=change["new_output_price"],
            detected_at=now,
            notified=False,
        )
        db.add(record)
        records.append(record)

    await db.commit()
    for r in records:
        await db.refresh(r)
    return records


def _direction_arrow(old: float, new: float) -> str:
    """Return an arrow indicating price direction."""
    if new > old:
        return "UP"
    elif new < old:
        return "DOWN"
    return "—"


def format_price_change_email(changes: list[dict[str, Any]]) -> str:
    """
    Return an HTML email body showing price changes.

    Includes model name, old -> new prices, percentage change, and direction.
    """
    if not changes:
        return "<p>No price changes detected.</p>"

    rows = []
    for c in changes:
        input_pct = _pct_change(c["old_input_price"], c["new_input_price"])
        output_pct = _pct_change(c["old_output_price"], c["new_output_price"])
        input_dir = _direction_arrow(c["old_input_price"], c["new_input_price"])
        output_dir = _direction_arrow(c["old_output_price"], c["new_output_price"])

        rows.append(f"""<tr>
  <td><strong>{c['model']}</strong></td>
  <td>{c['provider']}</td>
  <td>${c['old_input_price']:.6f} &rarr; ${c['new_input_price']:.6f} ({input_pct:+.2f}% {input_dir})</td>
  <td>${c['old_output_price']:.6f} &rarr; ${c['new_output_price']:.6f} ({output_pct:+.2f}% {output_dir})</td>
</tr>""")

    table_rows = "\n".join(rows)
    return f"""<html>
<body>
<h2>TokenBudget — Price Change Alert</h2>
<p>{len(changes)} model(s) have updated pricing:</p>
<table border="1" cellpadding="6" cellspacing="0">
<thead>
<tr><th>Model</th><th>Provider</th><th>Input Price (per 1K tokens)</th><th>Output Price (per 1K tokens)</th></tr>
</thead>
<tbody>
{table_rows}
</tbody>
</table>
<p>Review your budgets to ensure they reflect the new pricing.</p>
</body>
</html>"""


def format_price_change_slack(changes: list[dict[str, Any]]) -> str:
    """
    Return a Slack-formatted message (mrkdwn) showing price changes.
    """
    if not changes:
        return "No price changes detected."

    lines = [f"*TokenBudget — Price Change Alert*\n{len(changes)} model(s) have updated pricing:\n"]

    for c in changes:
        input_pct = _pct_change(c["old_input_price"], c["new_input_price"])
        output_pct = _pct_change(c["old_output_price"], c["new_output_price"])
        input_dir = _direction_arrow(c["old_input_price"], c["new_input_price"])
        output_dir = _direction_arrow(c["old_output_price"], c["new_output_price"])

        lines.append(
            f"*{c['model']}* ({c['provider']})\n"
            f"  Input: ${c['old_input_price']:.6f} → ${c['new_input_price']:.6f} ({input_pct:+.2f}% {input_dir})\n"
            f"  Output: ${c['old_output_price']:.6f} → ${c['new_output_price']:.6f} ({output_pct:+.2f}% {output_dir})"
        )

    return "\n".join(lines)
