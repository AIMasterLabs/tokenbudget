# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""AWS Bedrock provider integration."""
from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from tokenbudget.providers.base import BaseProvider
from tokenbudget.pricing import calculate_cost
from tokenbudget.types import UsageEvent

if TYPE_CHECKING:
    from tokenbudget.transport import EventTransport

logger = logging.getLogger(__name__)

# Map Bedrock model ID prefixes to provider names
_MODEL_PREFIX_MAP: list[tuple[str, str]] = [
    ("anthropic.claude-", "anthropic"),
    ("amazon.titan-", "amazon"),
    ("meta.llama", "meta"),
    ("ai21.", "ai21"),
    ("cohere.", "cohere"),
]


def _detect_provider_from_model(model_id: str) -> str:
    """Map a Bedrock model ID to a provider name."""
    for prefix, provider in _MODEL_PREFIX_MAP:
        if model_id.startswith(prefix):
            return provider
    return "bedrock"


def _extract_tokens_from_body(body: dict) -> tuple[int, int]:
    """Extract input/output token counts from the Bedrock response body.

    Different model families return usage information in different formats.
    """
    # Anthropic models: usage.input_tokens / usage.output_tokens
    usage = body.get("usage", {})
    if "input_tokens" in usage and "output_tokens" in usage:
        return usage["input_tokens"], usage["output_tokens"]

    # Amazon Titan models: inputTextTokenCount / results[0].tokenCount
    if "inputTextTokenCount" in body:
        input_tokens = body["inputTextTokenCount"]
        results = body.get("results", [{}])
        output_tokens = results[0].get("tokenCount", 0) if results else 0
        return input_tokens, output_tokens

    # Cohere / AI21 / Meta — look in generation metadata or token_count fields
    if "prompt_token_count" in body and "generation_token_count" in body:
        return body["prompt_token_count"], body["generation_token_count"]

    # Fallback: try amazon bedrock response metadata usage
    if "amazon-bedrock-invocationMetrics" in body:
        metrics = body["amazon-bedrock-invocationMetrics"]
        return metrics.get("inputTokenCount", 0), metrics.get("outputTokenCount", 0)

    return 0, 0


class BedrockProvider(BaseProvider):
    """Provider integration for AWS Bedrock Runtime (boto3)."""

    def detect(self, client: Any) -> bool:
        """Return True if the client is a boto3 Bedrock Runtime client."""
        # boto3 clients have a meta.service_model.service_name attribute
        try:
            service_name = client.meta.service_model.service_name
            return service_name == "bedrock-runtime"
        except (AttributeError, TypeError):
            return False

    def extract_event(self, response: Any, latency_ms: int, **kwargs: Any) -> UsageEvent:
        """Extract a UsageEvent from a Bedrock invoke_model response.

        Args:
            response: The parsed response body as a dict.
            latency_ms: Measured latency in milliseconds.
            **kwargs: Must include 'model_id' (the Bedrock model identifier).
        """
        from tokenbudget.context import get_current_tags

        model_id: str = kwargs.get("model_id", "unknown")
        provider = _detect_provider_from_model(model_id)

        body = response if isinstance(response, dict) else {}
        input_tokens, output_tokens = _extract_tokens_from_body(body)
        total_tokens = input_tokens + output_tokens

        # Try pricing with the full Bedrock model ID first, then fall back
        cost = calculate_cost(model_id, input_tokens, output_tokens)
        tags = get_current_tags()

        return UsageEvent(
            provider=provider,
            model=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            tags=tags,
        )

    def patch(self, client: Any, transport: "EventTransport") -> None:
        """Monkey-patch invoke_model and invoke_model_with_response_stream."""
        self._patch_invoke_model(client, transport)
        self._patch_invoke_model_stream(client, transport)

    def _patch_invoke_model(self, client: Any, transport: "EventTransport") -> None:
        """Patch invoke_model to intercept calls and track usage."""
        original_invoke = client.invoke_model

        def patched_invoke(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            response = original_invoke(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            try:
                model_id = kwargs.get("modelId", args[0] if args else "unknown")
                # Read and re-set the body stream
                raw_body = response["body"].read()
                response["body"] = _StreamWrapper(raw_body)
                body = json.loads(raw_body)

                # Also check response metadata for invocation metrics
                resp_metadata = response.get("ResponseMetadata", {})
                headers = resp_metadata.get("HTTPHeaders", {})
                if "x-amzn-bedrock-input-token-count" in headers:
                    body.setdefault("amazon-bedrock-invocationMetrics", {})
                    metrics = body["amazon-bedrock-invocationMetrics"]
                    metrics.setdefault(
                        "inputTokenCount",
                        int(headers.get("x-amzn-bedrock-input-token-count", 0)),
                    )
                    metrics.setdefault(
                        "outputTokenCount",
                        int(headers.get("x-amzn-bedrock-output-token-count", 0)),
                    )

                event = self.extract_event(body, latency_ms=elapsed_ms, model_id=model_id)
                transport.send(event)
            except Exception as exc:
                logger.warning("TokenBudget: failed to track Bedrock event: %s", exc)
            return response

        client.invoke_model = patched_invoke

    def _patch_invoke_model_stream(self, client: Any, transport: "EventTransport") -> None:
        """Patch invoke_model_with_response_stream to intercept streaming calls."""
        original_stream = client.invoke_model_with_response_stream

        def patched_stream(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            response = original_stream(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            try:
                model_id = kwargs.get("modelId", args[0] if args else "unknown")

                # For streaming, try to extract metrics from response metadata
                resp_metadata = response.get("ResponseMetadata", {})
                headers = resp_metadata.get("HTTPHeaders", {})
                input_tokens = int(headers.get("x-amzn-bedrock-input-token-count", 0))
                output_tokens = int(headers.get("x-amzn-bedrock-output-token-count", 0))

                if input_tokens or output_tokens:
                    body = {
                        "amazon-bedrock-invocationMetrics": {
                            "inputTokenCount": input_tokens,
                            "outputTokenCount": output_tokens,
                        }
                    }
                    event = self.extract_event(body, latency_ms=elapsed_ms, model_id=model_id)
                    transport.send(event)
            except Exception as exc:
                logger.warning("TokenBudget: failed to track Bedrock stream event: %s", exc)
            return response

        client.invoke_model_with_response_stream = patched_stream


class _StreamWrapper:
    """Minimal wrapper to allow re-reading a consumed boto3 StreamingBody."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, amt: int | None = None) -> bytes:
        if amt is None:
            result = self._data[self._pos:]
            self._pos = len(self._data)
        else:
            result = self._data[self._pos:self._pos + amt]
            self._pos += amt
        return result

    def close(self) -> None:
        pass


def wrap_bedrock(
    client: Any,
    api_key: str = "",
    endpoint: str = "",
    **kwargs: Any,
) -> Any:
    """Wrap a boto3 Bedrock Runtime client to track token usage.

    This is a convenience function that creates the transport and patches the client.
    boto3 is an optional dependency — it is only imported lazily.

    Args:
        client: A boto3 bedrock-runtime client instance.
        api_key: TokenBudget API key. Falls back to TOKENBUDGET_API_KEY env var.
        endpoint: Optional custom API endpoint.
        **kwargs: Additional config options (enabled, flush_interval, max_queue_size).

    Returns:
        The same client object, now patched to track usage.
    """
    try:
        import botocore  # noqa: F401
    except ImportError:
        raise ImportError(
            "boto3 is required for Bedrock support. "
            "Install it with: pip install tokenbudget[bedrock]"
        )

    from tokenbudget.config import TokenBudgetConfig
    from tokenbudget.transport import EventTransport

    config = TokenBudgetConfig(api_key=api_key, endpoint=endpoint, **kwargs)
    transport = EventTransport(config)
    provider = BedrockProvider()
    provider.patch(client, transport)
    return client
