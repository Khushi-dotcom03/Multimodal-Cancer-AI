from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from Breast_cancer.module4_breast_ai_assistant.schemas import ChatMessage, ChatRequest
from Breast_cancer.module4_breast_ai_assistant.service import (
    AssistantError,
    BreastCancerAssistantService,
    is_breast_cancer_related,
)


class FakeCompletionResult:
    def __init__(self, text=None, error=None):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text or "HER2 is a protein that can affect treatment choices."))]
        self.error = error


class FakeCompletions:
    def __init__(self, result=None, error=None):
        self.result = result or FakeCompletionResult()
        self.error = error
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


class FakeClient:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


class BreastAssistantServiceTests(unittest.TestCase):
    def setUp(self):
        self.completions = FakeCompletions()
        self.service = BreastCancerAssistantService(
            client_factory=lambda **_: FakeClient(self.completions)
        )
        self.key_patch = patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
        self.key_patch.start()
        self.addCleanup(self.key_patch.stop)

    def test_calls_groq_api_with_history(self):
        request = ChatRequest(
            message="Can you explain that more simply?",
            history=[
                ChatMessage(role="user", content="What does HER2-positive mean?"),
                ChatMessage(role="assistant", content="It means more HER2 protein is present."),
            ],
        )
        result = self.service.reply(request)

        self.assertIn("HER2", result.reply)
        self.assertEqual(self.completions.kwargs["model"], "openai/gpt-oss-20b")
        messages = self.completions.kwargs["messages"]
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Never diagnose", messages[0]["content"])
        self.assertEqual(messages[1], {"role": "user", "content": "What does HER2-positive mean?"})
        self.assertEqual(messages[2], {"role": "assistant", "content": "It means more HER2 protein is present."})
        self.assertEqual(messages[3], {"role": "user", "content": "Can you explain that more simply?"})
        self.assertIn("cannot diagnose", result.disclaimer)

    def test_rejects_clearly_unrelated_query(self):
        with self.assertRaises(AssistantError) as raised:
            self.service.reply(ChatRequest(message="How do I repair a bicycle?"))
        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.code, "out_of_scope")

    def test_rejects_other_cancer_even_if_it_mentions_treatment(self):
        with self.assertRaises(AssistantError) as raised:
            self.service.reply(ChatRequest(message="What is treatment for lung cancer?"))
        self.assertEqual(raised.exception.code, "out_of_scope")

    def test_follow_up_uses_breast_context(self):
        self.assertTrue(
            is_breast_cancer_related(
                "Can you explain that?",
                [ChatMessage(role="user", content="What does DCIS mean?")],
            )
        )

    def test_unrelated_new_topic_is_not_allowed_even_after_breast_context(self):
        self.assertFalse(
            is_breast_cancer_related(
                "How is the weather today?",
                [ChatMessage(role="user", content="What does DCIS mean?")],
            )
        )

    def test_other_cancer_follow_up_is_rejected(self):
        self.assertFalse(
            is_breast_cancer_related(
                "What is treatment for lung cancer?",
                [ChatMessage(role="user", content="What does DCIS mean?")],
            )
        )

    def test_missing_key_is_structured_configuration_error(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            with self.assertRaises(AssistantError) as raised:
                BreastCancerAssistantService().reply(ChatRequest(message="What is breast cancer?"))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.code, "missing_api_key")

    def test_maps_groq_rate_limit(self):
        self.completions.error = type("RateLimitError", (Exception,), {"status_code": 429})("limited")
        with self.assertRaises(AssistantError) as raised:
            self.service.reply(ChatRequest(message="What is breast cancer?"))
        self.assertEqual(raised.exception.status_code, 429)
        self.assertTrue(raised.exception.retryable)

    def test_maps_groq_connection_failure(self):
        self.completions.error = type("APIConnectionError", (Exception,), {})("offline")
        with self.assertRaises(AssistantError) as raised:
            self.service.reply(ChatRequest(message="What is breast cancer?"))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.code, "provider_unavailable")

    def test_maps_invalid_provider_credentials(self):
        self.completions.error = type("AuthenticationError", (Exception,), {"status_code": 401})("unauthorized")
        with self.assertRaises(AssistantError) as raised:
            self.service.reply(ChatRequest(message="What is breast cancer?"))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.code, "provider_configuration_error")


if __name__ == "__main__":
    unittest.main()
