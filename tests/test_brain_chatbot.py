"""Brain chatbot Groq integration tests; all provider traffic is mocked."""

from __future__ import annotations

import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from fastapi import HTTPException

from cancers.brain.chatbot import api, service
from cancers.brain.chatbot.api import ChatMessage, ChatRequest
from cancers.brain.chatbot.service import ChatProviderError


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def response_body(content: str | None = "Mock Groq answer.") -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode()


class BrainChatbotGroqTests(unittest.TestCase):
    def test_status_reports_key_presence_without_returning_key(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret", "BRAIN_CHATBOT_MODEL": "openai/gpt-oss-20b"}, clear=True):
            status = service.provider_status()
        self.assertEqual(status, {"configured": True, "provider": "Groq API", "model": "openai/gpt-oss-20b"})
        self.assertNotIn("test-only-secret", str(status))

    def test_missing_key_and_placeholder_are_not_configured(self):
        for key in (None, "", "your_key"):
            env = {"GROQ_API_KEY": key} if key is not None else {}
            with self.subTest(key_is_placeholder=key == "your_key"), patch.dict(os.environ, env, clear=True):
                self.assertFalse(service.provider_status()["configured"])
                with self.assertRaises(service.ProviderNotConfigured):
                    service._call_provider([{"role": "user", "content": "hello"}])

    def test_groq_request_preserves_system_context_and_conversation(self):
        messages = [
            {"role": "system", "content": service.SYSTEM_PROMPT},
            {"role": "system", "content": 'Context: {"mri":{"prediction":"glioma"}}'},
            {"role": "user", "content": "What does my result mean?"},
            {"role": "assistant", "content": "A model returned a result."},
            {"role": "user", "content": "Explain it."},
        ]
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret", "BRAIN_CHATBOT_MODEL": "openai/gpt-oss-20b"}, clear=True):
            with patch("cancers.brain.chatbot.service.urlopen", return_value=FakeResponse(response_body())) as mocked:
                answer = service.answer_chat(messages[-3:], {"mri": {"prediction": "glioma"}})

        self.assertEqual(answer, "Mock Groq answer.")
        self.assertEqual(mocked.call_count, 1)
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, service.GROQ_CHAT_COMPLETIONS_URL)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-only-secret")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "openai/gpt-oss-20b")
        self.assertEqual([item["role"] for item in payload["messages"]], ["system", "system", "user", "assistant", "user"])
        self.assertIn('"prediction":"glioma"', payload["messages"][1]["content"])
        self.assertNotIn("test-only-secret", answer)

    def test_chat_endpoint_keeps_existing_schema_and_never_returns_key(self):
        payload = response_body("A general educational answer.")
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret", "BRAIN_CHATBOT_MODEL": "openai/gpt-oss-20b"}, clear=True):
            with patch("cancers.brain.chatbot.service.urlopen", return_value=FakeResponse(payload)):
                result = api.brain_chat(ChatRequest(messages=[ChatMessage(role="user", content="What is glioma?")]))
        self.assertEqual(result, {"answer": "A general educational answer.", "provider": "Groq API", "model": "openai/gpt-oss-20b"})
        self.assertNotIn("test-only-secret", str(result))

    def test_rate_limit_is_manual_retry_and_makes_one_request(self):
        error = HTTPError(service.GROQ_CHAT_COMPLETIONS_URL, 429, "rate limited", None, io.BytesIO(b"{}"))
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret"}, clear=True):
            with patch("cancers.brain.chatbot.service.urlopen", side_effect=error) as mocked:
                with self.assertRaises(ChatProviderError) as raised:
                    service._call_provider([{"role": "user", "content": "hello"}])
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("retry manually", str(raised.exception))
        self.assertEqual(mocked.call_count, 1)

    def test_invalid_key_permission_and_unavailable_model_errors_are_distinct(self):
        for status, expected in ((401, "rejected the API key"), (403, "denied access"), (404, "model is unavailable")):
            error = HTTPError(service.GROQ_CHAT_COMPLETIONS_URL, status, "provider error", None, io.BytesIO(b"{}"))
            with self.subTest(status=status), patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret"}, clear=True):
                with patch("cancers.brain.chatbot.service.urlopen", side_effect=error):
                    with self.assertRaises(ChatProviderError) as raised:
                        service._call_provider([{"role": "user", "content": "hello"}])
            self.assertIn(expected, str(raised.exception))

    def test_network_malformed_and_empty_responses_are_handled(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret"}, clear=True):
            with patch("cancers.brain.chatbot.service.urlopen", side_effect=OSError("network down")):
                with self.assertRaises(ChatProviderError) as raised:
                    service._call_provider([{"role": "user", "content": "hello"}])
            self.assertEqual(raised.exception.status_code, 503)

            with patch("cancers.brain.chatbot.service.urlopen", return_value=FakeResponse(b"not json")):
                with self.assertRaises(ChatProviderError) as raised:
                    service._call_provider([{"role": "user", "content": "hello"}])
            self.assertEqual(raised.exception.status_code, 502)

            with patch("cancers.brain.chatbot.service.urlopen", return_value=FakeResponse(response_body("  "))):
                with self.assertRaises(ChatProviderError) as raised:
                    service._call_provider([{"role": "user", "content": "hello"}])
            self.assertEqual(raised.exception.status_code, 502)

    def test_api_returns_429_for_manual_retry_ui(self):
        error = HTTPError(service.GROQ_CHAT_COMPLETIONS_URL, 429, "rate limited", None, io.BytesIO(b"{}"))
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-only-secret"}, clear=True):
            with patch("cancers.brain.chatbot.service.urlopen", side_effect=error):
                with self.assertRaises(HTTPException) as raised:
                    api.brain_chat(ChatRequest(messages=[ChatMessage(role="user", content="hello")]))
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("retry manually", raised.exception.detail)


if __name__ == "__main__":
    unittest.main()
