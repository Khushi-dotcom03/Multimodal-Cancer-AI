# Brain Cancer Chatbot — Groq Provider

## Implementation

The existing Brain chatbot frontend and FastAPI routes remain unchanged. The backend sends the current system prompt, recent chat history, and optional untrusted Brain analysis context to Groq’s OpenAI-compatible chat completions endpoint. The configured model defaults to Groq-hosted `openai/gpt-oss-20b`; its namespace does not change the provider endpoint. No OpenAI API is called, and no OpenAI SDK dependency is used.

The backend reads `GROQ_API_KEY` from the repository-root `.env` file or process environment. The key is sent only in the backend Authorization header, never returned in status/chat responses, and never logged. One provider request is made per user submit; SDK/transport auto-retries are not used.

## Configuration

```ini
GROQ_API_KEY=your_key
BRAIN_CHATBOT_MODEL=qwen/qwen3.8-27b
```

`.env.example` keeps the key field empty. The status route reports key presence and selected model only; it does not validate the key or make a provider call.

## Errors

- Missing key: HTTP 503 with backend setup guidance.
- Invalid/rejected key: HTTP 503 with a clear credential message.
- Rate limit: HTTP 429 with wait-and-retry-manually guidance.
- Unavailable model: HTTP 503 with model/access guidance.
- Network or provider failure: HTTP 503.
- Malformed or empty response: HTTP 502.

## Model and free-tier status

Groq currently lists `openai/gpt-oss-20b` as a production model with Free Plan rate limits. The model page also lists paid Developer-plan token prices; users must stay on the Free tier to avoid pay-as-you-go charges. Free-tier quotas and model access are governed by the Groq account. No paid plan or billing setup is performed by this code.

See [Groq model catalog](https://console.groq.com/docs/models), [model details](https://console.groq.com/docs/model/openai/gpt-oss-20b), and [rate limits](https://console.groq.com/docs/rate-limits).
