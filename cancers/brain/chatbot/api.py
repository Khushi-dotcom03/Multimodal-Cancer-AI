"""Validated Brain chatbot endpoints."""

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cancers.brain.chatbot.service import ChatProviderError, ProviderNotConfigured, answer_chat, provider_status

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)
    analysis_context: dict[str, Any] = Field(default_factory=dict)


@router.get("/api/v1/cancers/brain/chat/status")
def brain_chat_status():
    return provider_status()


@router.post("/api/v1/cancers/brain/chat")
def brain_chat(request: ChatRequest):
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="The last chat message must be from the user.")
    context_bytes = len(json.dumps(request.analysis_context, ensure_ascii=False).encode("utf-8"))
    if context_bytes > 15_000:
        raise HTTPException(status_code=413, detail="Brain analysis context is too large. Clear it and retry.")
    messages = [item.model_dump() for item in request.messages]
    try:
        response = answer_chat(messages, request.analysis_context)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ChatProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"answer": response, "provider": provider_status()["provider"], "model": provider_status()["model"]}
