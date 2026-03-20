# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.context module."""
import pytest


def test_tags_context_manager_sets_tags():
    """tags() context manager sets tags within the block."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="production", team="ml"):
        current = get_current_tags()
        assert current["env"] == "production"
        assert current["team"] == "ml"


def test_tags_context_manager_clears_after_exit():
    """tags() context manager clears tags after block exits."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="production"):
        pass
    current = get_current_tags()
    assert "env" not in current


def test_get_current_tags_returns_empty_outside_context():
    """get_current_tags() returns empty dict outside any context."""
    from tokenbudget.context import get_current_tags
    tags_dict = get_current_tags()
    assert tags_dict == {}


def test_nested_tags_merge():
    """Nested tags() blocks merge inner with outer tags."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="production"):
        with tags(team="ml"):
            current = get_current_tags()
            assert current["env"] == "production"
            assert current["team"] == "ml"


def test_nested_tags_inner_overrides_outer():
    """Inner tags override outer tags on conflict."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="production"):
        with tags(env="staging"):
            current = get_current_tags()
            assert current["env"] == "staging"


def test_nested_tags_restore_outer_after_inner_exits():
    """After inner block exits, outer tags are restored."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="production"):
        with tags(team="ml"):
            pass
        current = get_current_tags()
        assert current["env"] == "production"
        assert "team" not in current


def test_tagged_decorator():
    """tagged() decorator wraps function with tags."""
    from tokenbudget.context import tagged, get_current_tags

    captured = {}

    @tagged(service="api", version="v1")
    def my_function():
        captured["tags"] = get_current_tags()

    my_function()
    assert captured["tags"]["service"] == "api"
    assert captured["tags"]["version"] == "v1"


def test_tagged_decorator_tags_cleared_after_call():
    """tagged() decorator clears tags after function returns."""
    from tokenbudget.context import tagged, get_current_tags

    @tagged(service="api")
    def my_function():
        pass

    my_function()
    current = get_current_tags()
    assert "service" not in current


def test_tagged_decorator_passes_args():
    """tagged() decorator passes arguments to the wrapped function."""
    from tokenbudget.context import tagged

    @tagged(env="test")
    def add(a, b):
        return a + b

    result = add(2, 3)
    assert result == 5


def test_tagged_decorator_passes_kwargs():
    """tagged() decorator passes keyword arguments to the wrapped function."""
    from tokenbudget.context import tagged

    @tagged(env="test")
    def greet(name="World"):
        return f"Hello, {name}!"

    result = greet(name="Alice")
    assert result == "Hello, Alice!"


def test_tags_context_manager_is_reusable():
    """tags() context manager can be used multiple times."""
    from tokenbudget.context import tags, get_current_tags
    with tags(env="prod"):
        assert get_current_tags()["env"] == "prod"
    with tags(env="staging"):
        assert get_current_tags()["env"] == "staging"
    assert get_current_tags() == {}
