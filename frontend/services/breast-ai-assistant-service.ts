export interface BreastAIMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface BreastAIResponse {
  request_id: string
  reply: string
  disclaimer: string
  model: string
}

export async function sendBreastAIMessage(
  message: string,
  history: BreastAIMessage[] = [],
): Promise<BreastAIResponse> {
  let response: Response

  try {
    response = await fetch('/api/proxy/breast-cancer-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
      cache: 'no-store',
    })
  } catch {
    throw new Error('Unable to connect to the Breast Cancer AI Assistant.')
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const errorMessage =
      data?.error?.message ||
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`

    throw new Error(errorMessage)
  }

  return data as BreastAIResponse
}
