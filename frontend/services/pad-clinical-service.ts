
import { apiRequest } from '@/lib/api-client'
import type { AnalysisResult } from '@/types'

export interface PADClinicalDetails {
  age: number
  region: string
  itch: string
  grew: string
  hurt: string
  changed: string
  bleed: string
  elevation: string
}

export interface PADClinicalRequest extends PADClinicalDetails {
  sex: 'female' | 'male' | 'unknown' | ''

}

export interface PADClinicalResult {
  analysisId: string
  cancerType: string
  moduleId: string
  dataset: string
  prediction: string
  classification: string
  confidence: number
  probabilities: Record<string, number>
  patient: PADClinicalRequest
  sexUsage?: string


  model: {
    name: string
    architecture: string
    inputFeaturesAfterPreprocessing: number
    trainingStatus: string
  }

  createdAt: string
  disclaimer: string
  reportStorage?: string
}

export const padClinicalAnalysisService = {
  async analyze(patient: PADClinicalRequest): Promise<PADClinicalResult> {
    const body = new FormData()

    Object.entries(patient).forEach(([key, value]) => {
      body.append(key, String(value))
    })

    return apiRequest<PADClinicalResult>(
      '/api/v1/cancers/skin/clinical-analysis',
      { method: 'POST', body, timeoutMs: 60_000 },
    )
  },
}

export const padFusionAnalysisService = {
  async analyze(file: File, patient: PADClinicalDetails, sex: 'female' | 'male' | 'unknown'): Promise<AnalysisResult> {
    const body = new FormData()

    body.append('file', file)
    body.append('sex', sex)

    Object.entries(patient).forEach(([key, value]) => {
      body.append(key, String(value))
    })

    return apiRequest<AnalysisResult>(
      '/api/v1/cancers/skin/pad-multimodal-analysis',
      { method: 'POST', body, timeoutMs: 180_000 },
    )
  },
}


