import { apiRequest, isApiConfigured } from '@/lib/api-client'
import type { BrainClinicalResult } from '@/services/brain-clinical-service'

export interface BrainMultimodalInput {
  file: File
  age: number
  sex: 'M' | 'F'
  site?: string
}

export interface BrainMultimodalResult {
  analysisId: string
  imageResult: {
    analysisId: string
    predictedClass: string
    classScores: Record<string, number>
    modelName: string
    architecture: string
    gradcam: { available: boolean; heatmap?: string | null; overlay?: string | null }
    disclaimer: string
  }
  clinicalResult: BrainClinicalResult
  resultScope: { kind: 'parallel_model_outputs'; fused: false; note: string }
}

export async function analyzeBrainMultimodal(input: BrainMultimodalInput): Promise<BrainMultimodalResult> {
  if (!isApiConfigured) throw new Error('Brain analysis backend is not configured. Start the FastAPI server and set NEXT_PUBLIC_API_URL.')
  const form = new FormData()
  form.append('file', input.file)
  form.append('age', String(input.age))
  form.append('sex', input.sex)
  if (input.site) form.append('site', input.site)
  return apiRequest<BrainMultimodalResult>('/api/v1/cancers/brain/multimodal-analysis', {
    method: 'POST',
    body: form,
    timeoutMs: 120_000,
  })
}
