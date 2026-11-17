import type { ApiError } from '@/types'

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? ''

export const isApiConfigured = API_BASE_URL.length > 0

export class ApiRequestError extends Error implements ApiError {
  status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: BodyInit | Record<string, unknown>
  timeoutMs?: number
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!isApiConfigured) {
    throw new ApiRequestError('Backend API is not configured. Set NEXT_PUBLIC_API_URL to connect.')
  }

  const { body, timeoutMs = 60_000, headers, ...rest } = options
  const isJsonBody = body !== undefined && !(body instanceof FormData) && typeof body === 'object' && !(body instanceof Blob)

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(isJsonBody ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
      body: isJsonBody ? JSON.stringify(body) : (body as BodyInit | undefined),
    })

    if (!response.ok) {
      let message = `Request failed with status ${response.status}`
      try {
        const data = await response.json()
        if (typeof data?.detail === 'string') message = data.detail
        else if (typeof data?.message === 'string') message = data.message
      } catch {}
      throw new ApiRequestError(message, response.status)
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiRequestError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiRequestError('The request timed out. Please try again.')
    }
    throw new ApiRequestError('Unable to reach the research backend. Check that the API server is running.')
  } finally {
    clearTimeout(timer)
  }
}
