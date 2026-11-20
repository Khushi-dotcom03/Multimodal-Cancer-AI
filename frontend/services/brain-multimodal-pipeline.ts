import type { AnalysisOutcome, AnalysisResult } from '@/types'
import type { BrainClinicalInput } from './brain-clinical-service'
import type { BrainMultimodalInput, BrainMultimodalResult } from './brain-multimodal-service'

export type PipelineStageName = 'mri' | 'clinical' | 'idh'
export type PipelineStageStatus = 'waiting' | 'running' | 'success' | 'failed' | 'skipped'

export type PipelineStage<T> =
  | { status: 'success'; result: T }
  | { status: Exclude<PipelineStageStatus, 'success'>; message?: string }

export interface BrainMultimodalPipelineResult {
  mri: PipelineStage<MRIScreeningResult>
  clinical: PipelineStage<BrainClinicalStageResult>
  idh: PipelineStage<BrainMultimodalResult>
}

export interface BrainClinicalStageResult {
  predictedSubtype: string
  predictedSubtypeLabel: string | null
  classScores: Record<string, number> | null
  scoreType: string
}

export interface MRIScreeningResult {
  /** Real selected model response when present; display fields remain usable without it. */
  selectedSlice?: AnalysisResult | null
  prediction: string
  classification: string
  confidence: number
  classScores?: Record<string, number>
  totalSlices: number
  tumorSlices: number
  selectedFileName: string
}

export interface MRIScreeningDisplay {
  prediction: string
  classification: string
  confidence: number
  classScores: Record<string, number> | null
  previewAvailable: boolean
  screeningLabel: 'Non-Tumor Detected' | 'Tumor Detected'
}

export function getMRIScreeningDisplay(result: MRIScreeningResult): MRIScreeningDisplay | null {
  if (!result || typeof result !== 'object') return null
  const prediction = result.prediction?.trim() || result.classification?.trim()
  if (!prediction) return null
  const classScores = result.classScores && Object.keys(result.classScores).length ? result.classScores : null
  return {
    prediction,
    classification: result.classification?.trim() || prediction,
    confidence: result.confidence,
    classScores,
    previewAvailable: Boolean(result.selectedSlice),
    screeningLabel: result.tumorSlices === 0 ? 'Non-Tumor Detected' : 'Tumor Detected',
  }
}

export interface BrainMultimodalPipelineInput {
  files: File[]
  clinical: BrainClinicalInput | null
  idh: Omit<BrainMultimodalInput, 'files'>
}

export interface BrainMultimodalPipelineDependencies {
  analyzeImage: (file: File) => Promise<AnalysisOutcome>
  // Accept unknown at this boundary: the standalone clinical route returns a
  // direct object, while older deployments may wrap it in clinicalResult/data.
  analyzeClinical: (input: BrainClinicalInput) => Promise<unknown>
  analyzeIdh: (input: BrainMultimodalInput) => Promise<BrainMultimodalResult>
}

type StageResult = MRIScreeningResult | BrainClinicalStageResult | BrainMultimodalResult
type StageUpdate = (stage: PipelineStageName, status: PipelineStageStatus, message?: string, result?: StageResult) => void

const skipped = (message: string) => ({ status: 'skipped' as const, message })

function normalizeImageClass(value: string): string {
  return value.trim().toLowerCase().replace(/[_-]+/g, ' ').replace(/\s+/g, ' ')
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function normalizeBrainClinicalStageResult(payload: unknown): BrainClinicalStageResult {
  const root = isRecord(payload) ? payload : null
  const nested = root && (root.clinicalResult ?? root.clinical_result ?? root.result ?? root.data)
  const source = isRecord(nested) ? nested : root
  if (!source) throw new Error('Clinical inference returned no result object.')

  const predictedSubtypeValue = source.predictedSubtype ?? source.predicted_subtype
  const predictedSubtypeLabelValue = source.predictedSubtypeLabel ?? source.predicted_subtype_label
  const predictedSubtype = typeof predictedSubtypeValue === 'string' && predictedSubtypeValue.trim()
    ? predictedSubtypeValue.trim()
    : ''
  const predictedSubtypeLabel = typeof predictedSubtypeLabelValue === 'string' && predictedSubtypeLabelValue.trim()
    ? predictedSubtypeLabelValue.trim()
    : ''
  if (!predictedSubtype && !predictedSubtypeLabel) {
    throw new Error('Clinical inference returned no predicted subtype.')
  }

  const rawScores = source.classScores ?? source.class_scores
  const scoreEntries: Array<[string, number]> = []
  if (isRecord(rawScores)) {
    for (const [label, value] of Object.entries(rawScores)) {
      if (typeof value === 'number' && Number.isFinite(value)) scoreEntries.push([label, value])
    }
  }
  const usableScores = scoreEntries.length ? Object.fromEntries(scoreEntries) : null
  const rawScoreType = source.scoreType ?? source.score_type

  return {
    predictedSubtype: predictedSubtype || predictedSubtypeLabel,
    predictedSubtypeLabel: predictedSubtypeLabel || null,
    classScores: usableScores,
    scoreType: typeof rawScoreType === 'string' ? rawScoreType : 'Uncalibrated model scores',
  }
}

export async function runBrainMultimodalPipeline(
  input: BrainMultimodalPipelineInput,
  dependencies: BrainMultimodalPipelineDependencies,
  onUpdate: StageUpdate = () => undefined,
): Promise<BrainMultimodalPipelineResult> {
  const tumorClasses = new Set(['glioma', 'meningioma', 'pituitary tumor'])
  const runMRI = async (): Promise<PipelineStage<MRIScreeningResult>> => {
    if (!input.files.length) {
      const message = 'Insufficient MRI input. Upload at least one MRI image to run MRI screening.'
      onUpdate('mri', 'skipped', message)
      return skipped(message)
    }
    onUpdate('mri', 'running', `Screening ${input.files.length} uploaded MRI slice${input.files.length === 1 ? '' : 's'}…`)
    try {
      const imagePredictions: Array<{ result: AnalysisResult; file: File; predictedClass: string }> = []
      for (const [index, file] of input.files.entries()) {
        onUpdate('mri', 'running', `Screening uploaded MRI slice ${index + 1} of ${input.files.length}…`)
        const outcome = await dependencies.analyzeImage(file)
        if (outcome.kind !== 'result' || outcome.result.isDemo) throw new Error(`The Brain Image model did not return a real prediction for ${file.name}.`)
        const predictedClass = normalizeImageClass(outcome.result.prediction || outcome.result.classification)
        if (!['glioma', 'meningioma', 'no tumor', 'pituitary tumor'].includes(predictedClass)) {
          throw new Error(`Unexpected Brain Image class returned for ${file.name}: ${outcome.result.prediction}`)
        }
        imagePredictions.push({ result: outcome.result, file, predictedClass })
      }

      const tumorPredictions = imagePredictions.filter(({ predictedClass }) => tumorClasses.has(predictedClass))
      const selectedPrediction = (tumorPredictions.length ? tumorPredictions : imagePredictions)
        .reduce((best, candidate) => candidate.result.confidence > best.result.confidence ? candidate : best)
      const mri: PipelineStage<MRIScreeningResult> = {
        status: 'success',
        result: {
          selectedSlice: selectedPrediction.result,
          prediction: selectedPrediction.result.prediction,
          classification: selectedPrediction.result.classification,
          confidence: selectedPrediction.result.confidence,
          classScores: selectedPrediction.result.classScores,
          totalSlices: imagePredictions.length,
          tumorSlices: tumorPredictions.length,
          selectedFileName: selectedPrediction.file.name,
        },
      }
      onUpdate('mri', 'success', undefined, mri.result)
      return mri
    } catch (error) {
      const message = error instanceof Error ? error.message : 'MRI screening failed.'
      onUpdate('mri', 'failed', message)
      return { status: 'failed', message }
    }
  }

  const runClinical = async (): Promise<PipelineStage<BrainClinicalStageResult>> => {
    if (!input.clinical) {
      const message = 'Insufficient clinical inputs. Age and sex are required; tumour location is optional.'
      onUpdate('clinical', 'skipped', message)
      return skipped(message)
    }
    onUpdate('clinical', 'running')
    try {
      const response = await dependencies.analyzeClinical(input.clinical)
      const result = normalizeBrainClinicalStageResult(response)
      onUpdate('clinical', 'success', undefined, result)
      return { status: 'success', result }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Clinical subtype classification failed.'
      onUpdate('clinical', 'failed', message)
      return { status: 'failed', message }
    }
  }

  const runIdh = async (): Promise<PipelineStage<BrainMultimodalResult>> => {
    if (!input.files.length) {
      const message = 'Insufficient MRI input. Upload at least one T1CE slice to run IDH classification.'
      onUpdate('idh', 'skipped', message)
      return skipped(message)
    }
    onUpdate('idh', 'running')
    try {
      const result = await dependencies.analyzeIdh({ ...input.idh, files: input.files })
      if (!result || typeof result !== 'object') {
        throw new Error('The IDH endpoint returned an empty result. Restart the Brain API and try again.')
      }
      onUpdate('idh', 'success', undefined, result)
      return { status: 'success', result }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'IDH molecular classification failed.'
      onUpdate('idh', 'failed', message)
      return { status: 'failed', message }
    }
  }

  // MRI screening is the gate: never call downstream inference until its real
  // model output confirms one of the known tumor classes.
  const mri = await runMRI()
  if (mri.status !== 'success') {
    const message = 'Skipped because MRI screening did not produce a tumor classification.'
    onUpdate('clinical', 'skipped', message)
    onUpdate('idh', 'skipped', message)
    return { mri, clinical: skipped(message), idh: skipped(message) }
  }

  const screeningClass = normalizeImageClass(
    mri.result.prediction || mri.result.classification,
  )
  if (screeningClass === 'no tumor') {
    const message = 'Skipped because MRI screening predicted No Tumor.'
    onUpdate('clinical', 'skipped', message)
    onUpdate('idh', 'skipped', message)
    return { mri, clinical: skipped(message), idh: skipped(message) }
  }

  if (!tumorClasses.has(screeningClass)) {
    const message = `Skipped because MRI screening returned an unsupported class: ${screeningClass || 'unknown'}.`
    onUpdate('clinical', 'skipped', message)
    onUpdate('idh', 'skipped', message)
    return { mri, clinical: skipped(message), idh: skipped(message) }
  }

  // Once a tumor is detected, execute the supported downstream stages.
  const [clinical, idh] = await Promise.all([runClinical(), runIdh()])
  return { mri, clinical, idh }
}
