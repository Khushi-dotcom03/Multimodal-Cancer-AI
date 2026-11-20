"""Validated request and response contracts for Breast Cancer Assistant."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4_000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4_000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def enforce_total_context_limit(self) -> "ChatRequest":
        total = len(self.message) + sum(len(item.content) for item in self.history)
        if total > 16_000:
            raise ValueError("The current message and conversation history may not exceed 16,000 characters.")
        return self


class ChatResponse(BaseModel):
    request_id: str
    reply: str
    disclaimer: str
    model: str


class ErrorBody(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorBody
