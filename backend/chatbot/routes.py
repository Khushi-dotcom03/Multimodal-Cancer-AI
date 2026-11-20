import logging
import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import AssistantProviderError, answer_question, configuration_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    conversationId: str | None = Field(default=None, max_length=80)
    cancerType: str = Field(default="skin", max_length=40)
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


@router.get("/status")
def status():
    return configuration_status()


@router.post("/chat")
def chat(payload: ChatRequest):
    request_id = uuid.uuid4().hex
    if payload.cancerType.strip().casefold() != "skin":
        logger.warning("assistant_request_rejected request_id=%s reason=skin_only", request_id)
        raise HTTPException(status_code=422, detail="The WeCure Assistant supports skin-cancer education only.")
    logger.info("assistant_request_started request_id=%s cancer_type=%s chars=%d history=%d", request_id, payload.cancerType, len(payload.message), len(payload.history))
    try:
        result = answer_question(message=payload.message.strip(), cancer_type=payload.cancerType, history=[message.model_dump() for message in payload.history])
    except AssistantProviderError as exc:
        logger.warning("assistant_provider_error request_id=%s error=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    logger.info("assistant_request_completed request_id=%s sources=%d", request_id, len(result["sources"]))
    return {"conversationId": payload.conversationId or uuid.uuid4().hex, "requestId": request_id, **result}
