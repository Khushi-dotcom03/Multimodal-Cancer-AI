export type CancerTypeId = 'skin'

export type ModuleStatus = 'available' | 'configuration-required' | 'coming-soon'

export type ModuleAccent = 'teal' | 'pink' | 'blue' | 'violet'

export interface ResearchModule {
  id: string
  name: string
  shortName: string
  description: string
  status: ModuleStatus
  statusLabel: string
  category: string
  imaging: string
  image: string
  accent: ModuleAccent
  href: string
}

export interface ClinicalDetails {
  age: number | null
  sex: 'male' | 'female' | 'unknown'
  localization: string
}

export interface PADClinicalDetails {
  age: number
  region: string
  itch: 'True' | 'False' | 'UNK'
  grew: 'True' | 'False' | 'UNK'
  hurt: 'True' | 'False' | 'UNK'
  changed: 'True' | 'False' | 'UNK'
  bleed: 'True' | 'False' | 'UNK'
  elevation: 'True' | 'False' | 'UNK'
}

export interface AnalysisRequest {
  cancerType?: CancerTypeId
  moduleId: string
  file: File
  age?: ClinicalDetails['age']
  sex?: ClinicalDetails['sex']
  localization?: ClinicalDetails['localization']
  dataset?: 'HAM10000' | 'PAD-UFES-20'
  padClinical?: PADClinicalDetails
}

export interface AnalysisResult {
  analysisId: string
  cancerType?: CancerTypeId
  moduleId: string
  prediction: string
  confidence: number
  classification: string
  classNames?: Record<string, string>
  fileName?: string
  patient?: ClinicalDetails
  reportStorage?: 'sqlite' | 'memory-only'
  probabilities?: Record<string, number>
  imageOnlyProbabilities?: Record<string, number>
  clinicalOnlyProbabilities?: Record<string, number>
  originalImageUrl?: string
  heatmapUrl?: string
  heatmapDescription?: string
  stage?: string
  grade?: string
  model: ModelInfo
  createdAt: string
  isDemo?: boolean
  classScores?: Record<string, number>
  gradcam?: { available: boolean; heatmap?: string | null; overlay?: string | null }
  disclaimer?: string
  inferenceStatus?: string
  validatorProbability?: number | null
}

export type AnalysisOutcome =
  | { kind: 'result'; result: AnalysisResult }
  | { kind: 'pending'; message: string }

export interface ModelInfo {
  name: string
  status?: 'available' | 'awaiting-data-and-model'
  imageModel?: string
  clinicalModel?: string
  fusion?: string
  architecture: string
  dataset: string
  version: string
  trainingStatus: string
  evaluationStatus: string
  lastUpdated: string
}

export type ReportStatus = 'completed' | 'pending' | 'failed'

export interface ResearchReport {
  analysisId: string
  cancerType?: CancerTypeId
  moduleId: string
  moduleName: string
  uploadDate: string
  modelStatus: 'connected' | 'pending'
  analysisStatus: ReportStatus
  fileName: string
  age?: number | null
  sex?: string
  localization?: string
  result?: AnalysisResult
  educationalOverview?: { overview: string; referenceTitle?: string; source?: string } | null
  researchReferences?: { title: string; url: string }[]
  evaluationMetrics?: ModelMetrics | null
  stage?: string
  grade?: string
  isDemo?: boolean
}

export interface ModelMetrics {
  accuracy: number
  precision: number
  recall: number
  f1: number
  macroF1?: number
  testSamples?: number
  confusionMatrix: { labels: string[]; matrix: number[][] }
}

export interface LibraryResource {
  id: string
  title: string
  type: 'Article' | 'Publication' | 'Dataset' | 'Tutorial' | 'Tool'
  category: string
  description: string
  url?: string
  isPlaceholder: boolean
}

export interface ApiError {
  message: string
  status?: number
}


