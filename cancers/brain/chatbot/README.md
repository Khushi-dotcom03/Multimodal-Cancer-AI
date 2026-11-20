# Brain AI Chatbot

The Brain AI Assistant is an educational chat interface for brain/CNS tumors, MRI terminology, pathology, biomarkers, and result summaries explicitly sent by the Brain analysis pages. It uses Groq’s OpenAI-compatible Chat Completions endpoint from the backend. No OpenAI client or OpenAI service is used. The key is never sent to or returned to the frontend. The assistant is not a diagnostic service or a substitute for a neuro-oncologist.

## Backend configuration

Add these settings to the repository-root `.env`. Keep the real key private and do not use a `NEXT_PUBLIC_` variable.

```ini
GROQ_API_KEY=your_key
BRAIN_CHATBOT_MODEL=openai/gpt-oss-20b
```

The backend loads `.env` from the repository root regardless of the shell’s current directory. Process environment variables take precedence. The default model is `openai/gpt-oss-20b`, a Groq-hosted production model. The `openai/` text is the model namespace; requests still go only to Groq's endpoint.

Groq currently lists GPT-OSS 20B as a production model with Free Plan rate limits. Stay on Groq’s Free tier to avoid usage charges. Groq also lists per-token Developer-plan prices; do not upgrade to that paid plan for this setup. Free-plan limits are account-specific and may change.

Install only the relevant backend dependencies if needed and start the API from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install python-dotenv
.\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000
```

The frontend uses `http://localhost:8000` by default during development. Set `NEXT_PUBLIC_API_URL` only to the backend base URL if it differs; never put the Groq key in frontend configuration.

Check configuration without making a model request:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/cancers/brain/chat/status
```

The status response reports whether a key is present and which model is selected. It does not validate the key or use quota.

## API and behavior

- `GET /api/v1/cancers/brain/chat/status`
- `POST /api/v1/cancers/brain/chat`

The existing request schema, recent conversation history, session-only Brain result context, and frontend retry behavior are preserved. The backend sends up to 12 conversation turns plus its system/context messages. It makes one provider request per submission; a 429 response asks the user to wait and retry manually.

Invalid credentials, rate limits, unavailable models, network/provider failures, and empty responses return clear API errors for the existing UI to display. The assistant uses only supplied Brain analysis context and general educational information. It must not diagnose cancer, invent patient findings, prescribe treatment, or claim medical validation.

See [Groq’s model catalog](https://console.groq.com/docs/models), [Qwen 3.8 27B model details](https://console.groq.com/docs/model/qwen/qwen3.8-27b), and [free/developer plan rate limits](https://console.groq.com/docs/rate-limits).
