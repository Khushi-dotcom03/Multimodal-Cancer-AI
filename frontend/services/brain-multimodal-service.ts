import { apiRequest, isApiConfigured } from '@/lib/api-client'

export interface BrainMultimodalInput {
  files: File[]
  ageAtImaging?: number
  sexAtBirth?: 'M' | 'F'
  tumorGrade?: number
  codeletion1p19q?: 'co-deleted' | 'non co-deleted'
  mgmt?: 'methylated' | 'unmethylated'
}

export interface BrainMultimodalResult {
  task: string
  predicted_class: 'wild type' | 'mutated'
  class_scores: Record<'wild type' | 'mutated', number>
  score_interpretation: string
  model: string
  n_slices_used: number
  checkpoint: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function normalizeBrainMultimodalResult(payload: unknown): BrainMultimodalResult {
  const root = isRecord(payload) ? payload : null
  const result = root && isRecord(root.result) ? root.result : root && isRecord(root.data) ? root.data : root
  if (!result) throw new Error('The IDH endpoint returned an empty response. Restart the Brain API and try again.')

  const predictedClass = result.predicted_class ?? result.predictedClass
  const rawScores = result.class_scores ?? result.classScores
  if (predictedClass !== 'wild type' && predictedClass !== 'mutated') {
    throw new Error('The IDH endpoint response is missing a valid predicted class. Restart the Brain API and try again.')
  }
  if (!isRecord(rawScores) || !['wild type', 'mutated'].every((label) => typeof rawScores[label] === 'number' && Number.isFinite(rawScores[label]))) {
    throw new Error('The IDH endpoint response is missing valid class scores. Restart the Brain API and try again.')
  }

  const nSlicesUsed = result.n_slices_used ?? result.nSlicesUsed
  const task = result.task
  const scoreInterpretation = result.score_interpretation ?? result.scoreInterpretation
  const model = result.model
  const checkpoint = result.checkpoint
  if (typeof nSlicesUsed !== 'number' || !Number.isFinite(nSlicesUsed) || nSlicesUsed < 1
      || typeof task !== 'string' || typeof scoreInterpretation !== 'string'
      || typeof model !== 'string' || typeof checkpoint !== 'string') {
    throw new Error('The IDH endpoint response is incomplete. Restart the Brain API and try again.')
  }

  return {
    task,
    predicted_class: predictedClass,
    class_scores: { 'wild type': rawScores['wild type'] as number, mutated: rawScores.mutated as number },
    score_interpretation: scoreInterpretation,
    model,
    n_slices_used: nSlicesUsed,
    checkpoint,
  }
}

export async function analyzeBrainMultimodal(input: BrainMultimodalInput): Promise<BrainMultimodalResult> {
  if (!isApiConfigured) throw new Error('Brain analysis backend is not configured. Start the FastAPI server and set NEXT_PUBLIC_API_URL.')
  if (!input.files.length) throw new Error('Select at least one T1CE MRI slice.')
  const form = new FormData()
  input.files.forEach((file) => form.append('files', file))
  if (input.ageAtImaging !== undefined) form.append('age_at_imaging', String(input.ageAtImaging))
  if (input.sexAtBirth) form.append('sex_at_birth', input.sexAtBirth)
  if (input.tumorGrade !== undefined) form.append('tumor_grade', String(input.tumorGrade))
  if (input.codeletion1p19q) form.append('codeletion_1p19q', input.codeletion1p19q)
  if (input.mgmt) form.append('mgmt', input.mgmt)
  const payload = await apiRequest<unknown>('/api/v1/cancers/brain/multimodal-idh-analysis', {
    method: 'POST',
    body: form,
    timeoutMs: 180_000,
  })
  return normalizeBrainMultimodalResult(payload)
}
