import { apiRequest, isApiConfigured } from '@/lib/api-client'
import type { ResearchReport } from '@/types'

export const reportsService = {
  async list(): Promise<ResearchReport[]> {
    if (!isApiConfigured) return []
    return apiRequest<ResearchReport[]>('/api/v1/reports')
  },

  async get(analysisId: string): Promise<ResearchReport> {
    return apiRequest<ResearchReport>(`/api/v1/reports/${encodeURIComponent(analysisId)}`)
  },

  downloadUrl(analysisId: string): string | null {
    if (!isApiConfigured) return null
    return `${process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '')}/api/v1/reports/${encodeURIComponent(analysisId)}/download`
  },
}
