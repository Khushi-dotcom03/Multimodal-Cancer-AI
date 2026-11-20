# Module 4 — Breast Cancer AI Assistant API

An independent FastAPI backend for educational breast-cancer conversations. It uses the Groq API via the official `groq` Python SDK, accepts recent conversation history for follow-ups, and keeps the Groq key on the server. It is not connected to the frontend or the root FastAPI app yet.

## Setup

From the repository root, install this module's dependencies into the Python environment used to run the API:

```powershell
python -m pip install -r Breast_cancer/module4_breast_ai_assistant/requirements.txt
Copy-Item Breast_cancer/module4_breast_ai_assistant/.env.example Breast_cancer/module4_breast_ai_assistant/.env
```

Set `GROQ_API_KEY` in that `.env` file or in the server environment. Never commit `.env`. `GROQ_MODEL` defaults to `openai/gpt-oss-20b` and can be set to a model available to your Groq account.

## Run independently

From the repository root:

```powershell
python -m uvicorn Breast_cancer.module4_breast_ai_assistant.app:app --host 127.0.0.1 --port 8010
```

OpenAPI documentation is available at `http://127.0.0.1:8010/docs`; health check: `GET /health`.

## Chat endpoint

`POST /api/v1/breast-cancer/chat`

```json
{
  "message": "What does HER2-positive mean?",
  "history": []
}
```

Send up to 12 prior `{ "role": "user" | "assistant", "content": "..." }` messages in chronological order. Each message is limited to 4,000 characters and combined context to 16,000 characters. The endpoint returns `request_id`, `reply`, `disclaimer`, and `model`. The client should append both the latest user message and assistant reply to its local history for the next follow-up.

Common errors use a structured JSON body:

```json
{
  "error": {
    "code": "missing_api_key",
    "message": "The Breast Cancer Assistant is not configured. Set GROQ_API_KEY on the API server.",
    "retryable": false
  }
}
```

Invalid fields/out-of-scope prompts return `422`; Groq rate limits return `429`; configuration/provider availability errors return `503`; other provider failures return `502`. API keys and user messages are never written to application logs.

## Smoke test

With the server running and `GROQ_API_KEY` configured:

```powershell
$body = @{ message = 'What does HER2-positive mean?'; history = @() } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8010/api/v1/breast-cancer/chat -ContentType 'application/json' -Body $body
```

To test contextual follow-up, pass the prior exchange in `history` and ask a short follow-up such as `Can you explain that more simply?`.

## Safety and privacy

The assistant provides general education only. It cannot diagnose, interpret an individual result as a diagnosis, prescribe or change treatment, or replace a qualified clinician. It encourages timely clinical follow-up for concerning changes and local emergency services for immediate danger. Screening advice varies by individual risk and location. Avoid including names, record numbers, or other identifying information; submitted conversation text is sent to the configured Groq API service to generate the answer.

To integrate later, include `Breast_cancer.module4_breast_ai_assistant.api.router` in the shared FastAPI app, install this module's `requirements.txt` dependencies, and register the standalone app's `RequestValidationError` handler if the same structured validation-error body is desired. This module currently does not modify that app.
