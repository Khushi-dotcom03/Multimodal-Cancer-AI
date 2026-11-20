export type BrainContextSource = 'brain_image' | 'brain_clinical' | 'brain_multimodal'

export interface BrainAnalysisContext {
  brain_image?: Record<string, unknown>
  brain_clinical?: Record<string, unknown>
  brain_multimodal?: Record<string, unknown>
}

const STORAGE_KEY = 'wecure.brain-chat.analysis-context.v1'

export function saveBrainChatContext(source: BrainContextSource, payload: Record<string, unknown>) {
  try {
    const current = getBrainChatContext() ?? {}
    const previous = current[source] ?? {}
    const next = { ...current, [source]: { ...previous, ...payload, capturedAt: new Date().toISOString() } }
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Chat remains useful without optional cross-page context persistence.
  }
}

export function getBrainChatContext(): BrainAnalysisContext | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw || raw.length > 15_000) return null
    const parsed = JSON.parse(raw) as BrainAnalysisContext
    return Object.keys(parsed).length ? parsed : null
  } catch {
    return null
  }
}

export function clearBrainChatContext() {
  try { sessionStorage.removeItem(STORAGE_KEY) } catch { /* session storage can be unavailable */ }
}

export function brainContextLabels(context: BrainAnalysisContext | null): string[] {
  if (!context) return []
  return [
    context.brain_image && 'MRI image result',
    context.brain_clinical && 'Clinical result',
    context.brain_multimodal && 'UTSW MRI + clinical result',
  ].filter((value): value is string => Boolean(value))
}
