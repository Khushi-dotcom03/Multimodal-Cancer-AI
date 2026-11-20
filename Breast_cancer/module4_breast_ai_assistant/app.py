"""Standalone FastAPI app for independent Module 4 backend development."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api import router


app = FastAPI(
    title="WeCure Breast Cancer AI Assistant API",
    description=(
        "Independent educational assistant API for breast cancer topics. "
        "It does not diagnose cancer or replace medical care."
    ),
    version="1.0.0",
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_request: Request, _exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_request",
                "message": "The request is invalid. Provide a non-empty message and up to 12 valid history messages within the documented size limits.",
                "retryable": False,
            }
        },
    )


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "module": "breast-cancer-ai-assistant"}
