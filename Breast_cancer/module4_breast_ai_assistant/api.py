"""REST router for Breast Cancer Module 4 AI Assistant."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .schemas import ChatRequest, ChatResponse, ErrorResponse
from .service import AssistantError, BreastCancerAssistantService


router = APIRouter(tags=["Breast Cancer AI Assistant"])
assistant_service = BreastCancerAssistantService()


@router.post(
    "/api/v1/breast-cancer/chat",
    response_model=ChatResponse,
    responses={
        422: {"model": ErrorResponse, "description": "Invalid request or out-of-scope question"},
        429: {"model": ErrorResponse, "description": "Groq rate limit reached"},
        502: {"model": ErrorResponse, "description": "Groq returned an error"},
        503: {"model": ErrorResponse, "description": "Assistant configuration or provider unavailable"},
    },
    summary="Ask the Breast Cancer AI Assistant",
    description=(
        "Answers breast-cancer-related educational questions. Pass recent user/assistant "
        "messages in `history` to maintain context. The endpoint does not diagnose or prescribe."
    ),
)
def breast_cancer_chat(payload: ChatRequest):
    try:
        return assistant_service.reply(payload)
    except AssistantError as exc:
        error = ErrorResponse(
            error={"code": exc.code, "message": exc.message, "retryable": exc.retryable}
        )
        return JSONResponse(status_code=exc.status_code, content=error.model_dump())
