import { apiRequest, isApiConfigured } from '@/lib/api-client'
import { RESEARCH_MODULES } from '@/lib/modules'
import type { ModelInfo, ModelMetrics, ResearchModule } from '@/types'

export const modulesService = {
  async list(): Promise<ResearchModule[]> {
    return RESEARCH_MODULES
  },

  async getModelInfo(moduleId: string): Promise<ModelInfo | null> {
    if (!isApiConfigured) return null
    return apiRequest<ModelInfo>(`/api/v1/modules/${moduleId}/model`)
  },

  async getMetrics(moduleId: string): Promise<ModelMetrics | null> {
    if (!isApiConfigured) return null
    return apiRequest<ModelMetrics>(`/api/v1/modules/${moduleId}/metrics`)
  },
}
