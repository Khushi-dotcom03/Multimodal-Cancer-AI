export type ModuleStatus = 'available' | 'coming-soon'

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

export interface AnalysisRequest {
  moduleId: string
  file: File
}

export interface AnalysisResult {
  analysisId: string
  moduleId: string
  prediction: string
  confidence: number
  classification: string
  heatmapUrl?: string
  model: ModelInfo
  createdAt: string
  isDemo?: boolean
}

export type AnalysisOutcome =
  | { kind: 'result'; result: AnalysisResult }
  | { kind: 'pending'; message: string }

export interface ModelInfo {
  name: string
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
  moduleId: string
  moduleName: string
  uploadDate: string
  modelStatus: 'connected' | 'pending'
  analysisStatus: ReportStatus
  fileName: string
  isDemo?: boolean
}

export interface ModelMetrics {
  accuracy: number
  precision: number
  recall: number
  f1: number
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
