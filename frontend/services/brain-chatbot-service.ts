import { apiRequest, isApiConfigured } from '@/lib/api-client'
import type { BrainAnalysisContext } from '@/lib/brain-chat-context'

export interface BrainChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface BrainChatStatus {
  configured: boolean
  provider: string
  model: string | null
}

export async function getBrainChatStatus() {
  if (!isApiConfigured) throw new Error('Backend API is not configured. Set NEXT_PUBLIC_API_URL and start the FastAPI server.')
  return apiRequest<BrainChatStatus>('/api/v1/cancers/brain/chat/status')
}

export async function sendBrainChat(messages: BrainChatMessage[], analysisContext: BrainAnalysisContext | null) {
  if (!isApiConfigured) throw new Error('Backend API is not configured. Set NEXT_PUBLIC_API_URL and start the FastAPI server.')
  return apiRequest<{ answer: string; provider: string; model: string | null }>('/api/v1/cancers/brain/chat', {
    method: 'POST',
    body: { messages: messages.slice(-12), analysis_context: analysisContext ?? {} },
    timeoutMs: 70_000,
  })
}
