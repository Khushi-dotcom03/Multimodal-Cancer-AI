"""Direct Groq-backed, skin-cancer-only educational assistant."""

from __future__ import annotations

import importlib.util
import os


SYSTEM_PROMPT = (
    "You are WeCure's Skin Cancer Assistant. Answer only general educational "
    "questions about skin cancer, skin lesions, prevention, diagnosis, and care. "
    "Explain terms such as BCC, melanoma, SCC, actinic keratosis, BKL, NV, DF, "
    "and vascular lesions as general concepts when asked. A model class label "
    "is not a diagnosis and does not establish what a person's lesion is. "
    "Never diagnose a person, assess an individual's image or symptoms, or "
    "interpret a model result as a diagnosis. Do not prescribe medication, "
    "recommend self-treatment, promise a cure, or claim clinical validation. "
    "For personal symptoms, a new or changing lesion, or an individual result, "
    "recommend evaluation by a qualified healthcare professional. Do not "
    "invent facts, citations, sources, clinicians, or medical credentials. "
    "If uncertain, say so. Do not answer questions about cancers outside the "
    "skin-cancer scope. Do not request personal identifying information."
)


class AssistantProviderError(RuntimeError):
    """Safe, user-displayable assistant configuration or provider error."""


def configuration_status() -> dict:
    missing = []
    if not os.getenv("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    if not os.getenv("WECURE_ASSISTANT_MODEL"):
        missing.append("WECURE_ASSISTANT_MODEL")
    if importlib.util.find_spec("groq") is None:
        missing.append("groq SDK dependency")

    configured = not missing
    return {
        "configured": configured,
        "mode": "provider" if configured else "unconfigured",
        "providerConfigured": configured,
        "missingConfiguration": missing,
        "message": (
            "Groq API is configured for skin-cancer education."
            if configured
            else "Configure GROQ_API_KEY and WECURE_ASSISTANT_MODEL in "
                 "backend/.env, and install the backend requirements."
        ),
    }


def answer_question(*, message: str, cancer_type: str, history: list[dict]) -> dict:
    if (cancer_type or "").strip().casefold() != "skin":
        raise AssistantProviderError(
            "The WeCure Assistant supports skin-cancer education only."
        )

    message = (message or "").strip()
    if not message:
        raise AssistantProviderError("Enter a question about skin-cancer education.")

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("WECURE_ASSISTANT_MODEL")
    if not api_key or not model:
        raise AssistantProviderError(
            "The Skin Cancer Assistant is not configured. Set GROQ_API_KEY "
            "and WECURE_ASSISTANT_MODEL in backend/.env."
        )

    # Import only when a configured chat request is made, so the API can start
    # and report a useful setup status even before optional dependencies install.
    try:
        from groq import Groq
    except ImportError:
        raise AssistantProviderError(
            "The Groq SDK is unavailable. Install the backend requirements "
            "and restart the API."
        ) from None

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for item in history[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            content = content.strip()
            if content:
                messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": message[:2000]})

    try:
        client = Groq(api_key=api_key, timeout=45.0, max_retries=0)
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_completion_tokens=800,
        )
        choices = getattr(completion, "choices", None) or []
        response_message = getattr(choices[0], "message", None) if choices else None
        answer = getattr(response_message, "content", None)
        if not isinstance(answer, str) or not answer.strip():
            raise AssistantProviderError(
                "The assistant provider returned an empty response. Please try again."
            )
        answer = answer.strip()
        if api_key in answer:
            answer = answer.replace(api_key, "[redacted]")
    except AssistantProviderError:
        raise
    except Exception as exc:
        # Exception text may contain request details. Log/report only the class.
        raise AssistantProviderError(
            f"The assistant provider request failed ({type(exc).__name__}). "
            "Please try again later."
        ) from None

    return {"answer": answer, "sources": [], "datasetMetadata": []}
