# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
Provider registry — canonical list of supported AI providers and their API details.

To add a new provider, append an entry to PROVIDERS with:
  - base_url: the provider's API root
  - key_header: the HTTP header used for authentication
"""

PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com",
        "key_header": "Authorization",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "key_header": "x-api-key",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com",
    },
}


def get_provider(name: str) -> dict:
    """Return provider config by name, or empty dict if unknown."""
    return PROVIDERS.get(name, {})
