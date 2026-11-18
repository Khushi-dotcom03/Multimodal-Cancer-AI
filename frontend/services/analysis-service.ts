import { apiRequest, isApiConfigured } from '@/lib/api-client'
import type { AnalysisOutcome, AnalysisRequest, AnalysisResult } from '@/types'

export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png'] as const
export const ACCEPTED_EXTENSIONS = ['.jpg', '.jpeg', '.png'] as const
export const MAX_IMAGE_SIZE_MB = 10
export const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

export const MODEL_PENDING_MESSAGE =
  'Model integration pending. Connect the trained ML model to view research results.'

export function validateImageFile(file: File): string | null {
  const name = file.name.toLowerCase()
  const hasValidExtension = ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))
  const hasValidType = (ACCEPTED_IMAGE_TYPES as readonly string[]).includes(file.type)
  if (!hasValidExtension || !hasValidType) {
    return 'Unsupported file format. Please upload a JPG, JPEG, or PNG image.'
  }
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    return `File is too large. Maximum size is ${MAX_IMAGE_SIZE_MB} MB.`
  }
  if (file.size === 0) {
    return 'The selected file is empty.'
  }
  return null
}

export const analysisService = {
  async analyze({ cancerType, moduleId, file, age, sex, localization }: AnalysisRequest): Promise<AnalysisOutcome> {
    if (!isApiConfigured) {
      if (moduleId === 'brain-tumour') {
        throw new Error('Brain MRI analysis backend is not configured. Set NEXT_PUBLIC_API_URL and start the FastAPI server.')
      }
      await new Promise((r) => setTimeout(r, 900))
      return { kind: 'pending', message: MODEL_PENDING_MESSAGE }
    }

    const form = new FormData()
    form.append('file', file)
    if (moduleId !== 'skin-image-analysis' && moduleId !== 'brain-tumour') {
      if (age != null) form.append('age', String(age))
      if (sex) form.append('sex', sex)
      if (localization) form.append('localization', localization)
    }
    const path = moduleId === 'brain-tumour'
      ? '/api/v1/analysis/brain-tumour'
      : moduleId === 'skin-image-analysis'
        ? `/api/v1/cancers/${cancerType ?? 'skin'}/image-analysis`
        : `/api/v1/cancers/${cancerType ?? 'skin'}/multimodal-analysis`
    const result = await apiRequest<AnalysisResult>(path, {
      method: 'POST',
      body: form,
      timeoutMs: 120_000,
    })
    return { kind: 'result', result }
  },
}
