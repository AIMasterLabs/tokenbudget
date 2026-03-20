# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""TokenBudget context management — tags via contextvars."""
from __future__ import annotations

import functools
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable

_current_tags: ContextVar[dict[str, Any]] = ContextVar("_current_tags", default={})


def get_current_tags() -> dict[str, Any]:
    """Return the current context tags (empty dict if none set)."""
    return dict(_current_tags.get())


@contextmanager
def tags(**kwargs: Any):
    """Context manager that sets tags for all events within the block.

    Supports nesting: inner tags merge with (and override) outer tags.
    """
    # Merge outer tags with new tags (new tags take precedence)
    outer = _current_tags.get()
    merged = {**outer, **kwargs}
    token = _current_tags.set(merged)
    try:
        yield
    finally:
        _current_tags.reset(token)


def tagged(**kwargs: Any) -> Callable:
    """Decorator that wraps a function in a tags() context manager."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kw: Any) -> Any:
            with tags(**kwargs):
                return fn(*args, **kw)
        return wrapper
    return decorator
