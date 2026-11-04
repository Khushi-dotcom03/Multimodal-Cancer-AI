import type { AnalysisResult, LibraryResource, ModelInfo, ModelMetrics, ResearchReport } from '@/types'

/**
 * Illustrative values used only when the user turns on Demo Mode.
 * None of these numbers represent real model performance or real analyses.
 */

export const DEMO_MODEL_INFO: ModelInfo = {
  name: 'Demo CNN Classifier',
  architecture: 'Illustrative placeholder (e.g. EfficientNet / ResNet)',
  dataset: 'Placeholder dataset name',
  version: 'v0.0-demo',
  trainingStatus: 'Not trained (demo)',
  evaluationStatus: 'Not evaluated (demo)',
  lastUpdated: '—',
}

export const PENDING_MODEL_INFO: ModelInfo = {
  name: 'Not connected',
  architecture: 'Pending backend integration',
  dataset: 'Pending',
  version: '—',
  trainingStatus: 'Pending',
  evaluationStatus: 'Pending',
  lastUpdated: '—',
}

export const DEMO_METRICS: ModelMetrics = {
  accuracy: 0.82,
  precision: 0.79,
  recall: 0.76,
  f1: 0.77,
  confusionMatrix: {
    labels: ['Class A', 'Class B', 'Class C'],
    matrix: [
      [42, 6, 2],
      [7, 35, 8],
      [3, 5, 40],
    ],
  },
}

export const DEMO_ACTIVITY = [
  { month: 'Jan', analyses: 12, reports: 4 },
  { month: 'Feb', analyses: 18, reports: 7 },
  { month: 'Mar', analyses: 15, reports: 6 },
  { month: 'Apr', analyses: 24, reports: 10 },
  { month: 'May', analyses: 21, reports: 9 },
  { month: 'Jun', analyses: 30, reports: 13 },
]

export const DEMO_MODEL_COMPARISON = [
  { metric: 'Accuracy', modelA: 82, modelB: 78, modelC: 74 },
  { metric: 'Precision', modelA: 79, modelB: 81, modelC: 70 },
  { metric: 'Recall', modelA: 76, modelB: 72, modelC: 77 },
  { metric: 'F1', modelA: 77, modelB: 76, modelC: 73 },
]

export const DEMO_DATASET_SPLIT = [
  { name: 'Training', value: 70 },
  { name: 'Validation', value: 15 },
  { name: 'Test', value: 15 },
]

export const DEMO_CLASS_DISTRIBUTION = [
  { name: 'Class A', count: 320 },
  { name: 'Class B', count: 210 },
  { name: 'Class C', count: 140 },
  { name: 'Class D', count: 90 },
  { name: 'Class E', count: 60 },
]

export const DEMO_REPORTS: ResearchReport[] = [
  { analysisId: 'DEMO-0001', moduleId: 'skin-cancer', moduleName: 'Skin Cancer', uploadDate: '2026-04-02', modelStatus: 'pending', analysisStatus: 'completed', fileName: 'sample_lesion_01.jpg', isDemo: true },
  { analysisId: 'DEMO-0002', moduleId: 'skin-cancer', moduleName: 'Skin Cancer', uploadDate: '2026-04-05', modelStatus: 'pending', analysisStatus: 'pending', fileName: 'sample_lesion_02.png', isDemo: true },
  { analysisId: 'DEMO-0003', moduleId: 'skin-cancer', moduleName: 'Skin Cancer', uploadDate: '2026-04-07', modelStatus: 'pending', analysisStatus: 'failed', fileName: 'sample_lesion_03.jpg', isDemo: true },
  { analysisId: 'DEMO-0004', moduleId: 'skin-cancer', moduleName: 'Skin Cancer', uploadDate: '2026-04-09', modelStatus: 'pending', analysisStatus: 'completed', fileName: 'sample_lesion_04.jpeg', isDemo: true },
  { analysisId: 'DEMO-0005', moduleId: 'skin-cancer', moduleName: 'Skin Cancer', uploadDate: '2026-04-10', modelStatus: 'pending', analysisStatus: 'pending', fileName: 'sample_lesion_05.png', isDemo: true },
]

export function buildDemoAnalysisResult(moduleId: string): AnalysisResult {
  return {
    analysisId: `DEMO-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
    moduleId,
    prediction: 'Demo Label (not a prediction)',
    confidence: 0,
    classification: 'Illustrative output — no model was run',
    model: DEMO_MODEL_INFO,
    createdAt: new Date().toISOString(),
    isDemo: true,
  }
}

export const LIBRARY_RESOURCES: LibraryResource[] = [
  { id: 'r1', title: 'Placeholder: Skin lesion classification survey', type: 'Publication', category: 'Skin Cancer', description: 'Slot for a peer-reviewed survey on deep learning approaches to dermoscopic image classification. Add the verified citation and link.', isPlaceholder: true },
  { id: 'r2', title: 'Placeholder: Dermoscopy dataset reference', type: 'Dataset', category: 'Skin Cancer', description: 'Slot for the dermoscopic image dataset used to train and evaluate the skin research model.', isPlaceholder: true },
  { id: 'r3', title: 'Placeholder: Convolutional neural networks primer', type: 'Tutorial', category: 'AI & Deep Learning', description: 'Slot for an introductory resource on CNN architectures for medical image analysis.', isPlaceholder: true },
  { id: 'r4', title: 'Placeholder: Explainable AI for medical imaging', type: 'Article', category: 'Explainable AI', description: 'Slot for a resource on saliency maps, Grad-CAM and interpretability methods in clinical imaging research.', isPlaceholder: true },
  { id: 'r5', title: 'Placeholder: Multimodal learning in oncology', type: 'Publication', category: 'Multimodal ML', description: 'Slot for research combining imaging, clinical records and genomics for cancer research.', isPlaceholder: true },
  { id: 'r6', title: 'Placeholder: Breast imaging research overview', type: 'Article', category: 'Breast Cancer', description: 'Slot for background reading supporting the future Breast Cancer research module.', isPlaceholder: true },
  { id: 'r7', title: 'Placeholder: Lung CT analysis resources', type: 'Article', category: 'Lung Cancer', description: 'Slot for background reading supporting the future Lung Cancer research module.', isPlaceholder: true },
  { id: 'r8', title: 'Placeholder: Brain MRI segmentation tools', type: 'Tool', category: 'Brain Tumour', description: 'Slot for tooling and references supporting the future Brain Tumour research module.', isPlaceholder: true },
  { id: 'r9', title: 'Placeholder: Model evaluation metrics guide', type: 'Tutorial', category: 'AI & Deep Learning', description: 'Slot for a guide on accuracy, precision, recall, F1 and confusion matrices in imbalanced medical datasets.', isPlaceholder: true },
]

export const LIBRARY_CATEGORIES = Array.from(new Set(LIBRARY_RESOURCES.map((r) => r.category)))
