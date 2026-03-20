# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""Tests for tokenbudget.providers.bedrock module."""
import json
import pytest
from unittest.mock import MagicMock, patch


def make_mock_bedrock_client():
    """Create a mock boto3 bedrock-runtime client."""
    client = MagicMock()
    client.meta.service_model.service_name = "bedrock-runtime"
    return client


def make_invoke_model_response(body_dict, headers=None):
    """Create a mock invoke_model response."""
    raw_bytes = json.dumps(body_dict).encode()
    body_stream = MagicMock()
    body_stream.read.return_value = raw_bytes

    response = {
        "body": body_stream,
        "ResponseMetadata": {
            "HTTPHeaders": headers or {},
        },
    }
    return response


def make_stream_response(headers=None):
    """Create a mock invoke_model_with_response_stream response."""
    return {
        "body": MagicMock(),
        "ResponseMetadata": {
            "HTTPHeaders": headers or {},
        },
    }


class TestBedrockProviderDetect:
    """Tests for BedrockProvider.detect()."""

    def test_detects_bedrock_client(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        client = make_mock_bedrock_client()
        assert provider.detect(client) is True

    def test_does_not_detect_non_bedrock(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        client = MagicMock()
        del client.meta  # ensure no meta attribute
        assert provider.detect(client) is False

    def test_does_not_detect_other_boto3_service(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        client = MagicMock()
        client.meta.service_model.service_name = "s3"
        assert provider.detect(client) is False


class TestModelIdMapping:
    """Tests for _detect_provider_from_model."""

    def test_anthropic_claude(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("anthropic.claude-3-5-sonnet") == "anthropic"
        assert _detect_provider_from_model("anthropic.claude-3-haiku") == "anthropic"

    def test_amazon_titan(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("amazon.titan-text-express") == "amazon"

    def test_meta_llama(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("meta.llama3-70b-instruct") == "meta"

    def test_ai21(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("ai21.j2-ultra") == "ai21"

    def test_cohere(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("cohere.command-r") == "cohere"

    def test_unknown_model(self):
        from tokenbudget.providers.bedrock import _detect_provider_from_model
        assert _detect_provider_from_model("unknown.model-v1") == "bedrock"


class TestExtractTokens:
    """Tests for token extraction from various response formats."""

    def test_anthropic_format(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        body = {"usage": {"input_tokens": 100, "output_tokens": 50}}
        event = provider.extract_event(body, latency_ms=200, model_id="anthropic.claude-3-5-sonnet")
        assert event.input_tokens == 100
        assert event.output_tokens == 50
        assert event.total_tokens == 150
        assert event.provider == "anthropic"
        assert event.model == "anthropic.claude-3-5-sonnet"

    def test_titan_format(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        body = {
            "inputTextTokenCount": 80,
            "results": [{"tokenCount": 40, "outputText": "hello"}],
        }
        event = provider.extract_event(body, latency_ms=150, model_id="amazon.titan-text-express")
        assert event.input_tokens == 80
        assert event.output_tokens == 40
        assert event.provider == "amazon"

    def test_invocation_metrics_format(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        body = {
            "amazon-bedrock-invocationMetrics": {
                "inputTokenCount": 200,
                "outputTokenCount": 100,
            }
        }
        event = provider.extract_event(body, latency_ms=100, model_id="meta.llama3-70b-instruct")
        assert event.input_tokens == 200
        assert event.output_tokens == 100
        assert event.provider == "meta"

    def test_cost_calculated_for_known_model(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        body = {"usage": {"input_tokens": 1000, "output_tokens": 500}}
        event = provider.extract_event(
            body, latency_ms=200, model_id="anthropic.claude-3-5-sonnet"
        )
        assert event.cost_usd > 0.0


class TestPatchInvokeModel:
    """Tests for patching invoke_model."""

    def test_patch_replaces_invoke_model(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()
        original = client.invoke_model

        provider.patch(client, transport)
        assert client.invoke_model != original

    def test_patch_calls_transport_send(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()

        body_dict = {"usage": {"input_tokens": 10, "output_tokens": 5}}
        response = make_invoke_model_response(body_dict)
        client.invoke_model.return_value = response

        provider.patch(client, transport)
        result = client.invoke_model(modelId="anthropic.claude-3-5-sonnet", body=b'{}')

        transport.send.assert_called_once()
        event = transport.send.call_args[0][0]
        assert event.model == "anthropic.claude-3-5-sonnet"
        assert event.input_tokens == 10
        assert event.output_tokens == 5

    def test_response_body_still_readable(self):
        """After patching, the response body should still be readable."""
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()

        body_dict = {"usage": {"input_tokens": 10, "output_tokens": 5}, "content": "hello"}
        response = make_invoke_model_response(body_dict)
        client.invoke_model.return_value = response

        provider.patch(client, transport)
        result = client.invoke_model(modelId="anthropic.claude-3-5-sonnet", body=b'{}')

        # Body should be re-readable
        raw = result["body"].read()
        parsed = json.loads(raw)
        assert parsed["content"] == "hello"

    def test_patch_never_breaks_user_code(self):
        """Tracking errors should not propagate to the user."""
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        transport.send.side_effect = RuntimeError("Transport error")
        client = make_mock_bedrock_client()

        body_dict = {"usage": {"input_tokens": 10, "output_tokens": 5}}
        response = make_invoke_model_response(body_dict)
        client.invoke_model.return_value = response

        provider.patch(client, transport)
        # Should NOT raise
        result = client.invoke_model(modelId="anthropic.claude-3-5-sonnet", body=b'{}')
        assert result is not None


class TestPatchStreaming:
    """Tests for patching invoke_model_with_response_stream."""

    def test_patch_replaces_stream_method(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()
        original = client.invoke_model_with_response_stream

        provider.patch(client, transport)
        assert client.invoke_model_with_response_stream != original

    def test_streaming_intercepts_with_headers(self):
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()

        headers = {
            "x-amzn-bedrock-input-token-count": "50",
            "x-amzn-bedrock-output-token-count": "25",
        }
        response = make_stream_response(headers=headers)
        client.invoke_model_with_response_stream.return_value = response

        provider.patch(client, transport)
        result = client.invoke_model_with_response_stream(
            modelId="anthropic.claude-3-haiku", body=b'{}'
        )

        transport.send.assert_called_once()
        event = transport.send.call_args[0][0]
        assert event.input_tokens == 50
        assert event.output_tokens == 25
        assert event.provider == "anthropic"

    def test_streaming_no_headers_no_event(self):
        """If no token headers present, no event is sent."""
        from tokenbudget.providers.bedrock import BedrockProvider
        provider = BedrockProvider()
        transport = MagicMock()
        client = make_mock_bedrock_client()

        response = make_stream_response(headers={})
        client.invoke_model_with_response_stream.return_value = response

        provider.patch(client, transport)
        client.invoke_model_with_response_stream(modelId="anthropic.claude-3-haiku", body=b'{}')

        transport.send.assert_not_called()


class TestWrapBedrock:
    """Tests for the wrap_bedrock convenience function."""

    def test_wrap_bedrock_patches_client(self):
        from tokenbudget.providers.bedrock import wrap_bedrock
        client = make_mock_bedrock_client()
        original_invoke = client.invoke_model

        result = wrap_bedrock(client, api_key="test-key")

        assert result is client
        assert client.invoke_model != original_invoke

    def test_wrap_bedrock_importable_from_top_level(self):
        from tokenbudget import wrap_bedrock
        assert callable(wrap_bedrock)


class TestBoto3ImportError:
    """Test graceful error when boto3 is not installed."""

    def test_wrap_bedrock_raises_on_missing_boto3(self):
        import sys
        from unittest.mock import patch as mock_patch

        # Temporarily make botocore unimportable
        with mock_patch.dict(sys.modules, {"botocore": None}):
            from tokenbudget.providers.bedrock import wrap_bedrock
            client = MagicMock()
            with pytest.raises(ImportError, match="boto3 is required"):
                wrap_bedrock(client, api_key="test-key")
