'use client'

import { useEffect, useState } from 'react'
import { DemoBanner } from '@/components/common/brand'
import { useDemoMode } from '@/components/providers'
import { analysisService } from '@/services/analysis-service'
import type { AnalysisOutcome } from '@/types'
import { AnalysisControls } from './analysis-controls'
import { AnalysisResults } from './analysis-results'
import { ImageUploader } from './image-uploader'

export type AnalysisPhase = 'idle' | 'uploading' | 'processing' | 'done' | 'error'

export function AnalysisWorkspace() {
  const { demoMode, setDemoMode } = useDemoMode()
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [phase, setPhase] = useState<AnalysisPhase>('idle')
  const [outcome, setOutcome] = useState<AnalysisOutcome | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const handleFile = (next: File | null) => {
    setFile(next)
    setOutcome(null)
    setError(null)
    setPhase('idle')
  }

  const analyze = async () => {
    if (!file) return
    setError(null)
    setOutcome(null)
    setPhase('uploading')
    const toProcessing = setTimeout(() => setPhase('processing'), 500)
    try {
      const result = await analysisService.analyze({ moduleId: 'skin-cancer', file }, { demo: demoMode })
      setOutcome(result)
      setPhase('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed. Please try again.')
      setPhase('error')
    } finally {
      clearTimeout(toProcessing)
    }
  }

  const busy = phase === 'uploading' || phase === 'processing'

  return (
    <div className="flex flex-col gap-6">
      {demoMode && <DemoBanner message="Analysis returns an illustrative placeholder. No model is run and no prediction is made." />}
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <ImageUploader file={file} previewUrl={previewUrl} onFileChange={handleFile} disabled={busy} />
        </div>
        <div className="xl:col-span-2">
          <AnalysisControls
            file={file}
            phase={phase}
            onAnalyze={analyze}
            demoMode={demoMode}
            onDemoModeChange={setDemoMode}
          />
        </div>
      </div>
      <AnalysisResults phase={phase} outcome={outcome} error={error} previewUrl={previewUrl} onRetry={analyze} />
    </div>
  )
}
