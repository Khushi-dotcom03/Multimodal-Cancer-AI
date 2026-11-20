import { apiRequest } from '@/lib/api-client'

export interface AssistantStatus {
  configured: boolean
  mode: 'unconfigured' | 'provider'
  providerConfigured: boolean
  missingConfiguration: string[]
  message: string
}

export interface AssistantChatResponse {
  answer: string
  sources: { title: string; organization: string; topic: string; url: string }[]
  datasetMetadata: {
    name: string
    task: string
    manifest: string
    status: string
    accessUrl?: string
  }[]
  conversationId: string
  requestId: string
}

export const assistantService = {
  status: () => apiRequest<AssistantStatus>('/api/v1/assistant/status'),
  ask(payload: {
    message: string
    cancerType: 'skin'
    history: { role: 'user' | 'assistant'; content: string }[]
    conversationId?: string
  }) {
    return apiRequest<AssistantChatResponse>('/api/v1/assistant/chat', {
      method: 'POST',
      body: payload,
    })
  },
}
