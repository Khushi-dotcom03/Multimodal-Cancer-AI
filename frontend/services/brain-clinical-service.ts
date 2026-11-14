import { apiRequest, isApiConfigured } from '@/lib/api-client'

export interface BrainClinicalInput {
  age: number
  sex: 'M' | 'F'
  site?: string
}

export interface BrainClinicalResult {
  analysisId: string
  predictedSubtype: string
  predictedSubtypeLabel: string
  classScores: Record<string, number>
  scoreType: string
  model: {
    name: string
    architecture: string
    dataset: string
    features: string[]
    target: string
    testMetrics: {
      accuracy: number
      balanced_accuracy: number
      macro_precision: number
      macro_recall: number
      macro_f1: number
      per_class: Record<string, { precision: number; recall: number; f1: number; support: number }>
    }
    majorityBaseline: { macro_f1: number }
    validationMacroF1: number
  }
  inputSummary: { age: number; sex: string; site: string }
  disclaimer: string
  inferenceStatus: string
}

export async function analyzeBrainClinical(input: BrainClinicalInput): Promise<BrainClinicalResult> {
  if (!isApiConfigured) {
    throw new Error('Brain Clinical backend is not configured. Start the FastAPI server and set NEXT_PUBLIC_API_URL.')
  }
  return apiRequest<BrainClinicalResult>('/api/v1/cancers/brain/clinical-analysis', {
    method: 'POST',
    body: { age: input.age, sex: input.sex, site: input.site },
    timeoutMs: 60_000,
  })
}
