'use client'

import { useEffect, useState } from 'react'
import { analysisService } from '@/services/analysis-service'
import type { AnalysisOutcome, ClinicalDetails } from '@/types'
import { AnalysisControls } from './analysis-controls'
import { AnalysisResults } from './analysis-results'
import { ImageUploader } from './image-uploader'
import { CombinedAnalysisWorkspace } from './combined-analysis-workspace'

export type AnalysisPhase = 'idle' | 'uploading' | 'processing' | 'done' | 'error'

export function AnalysisWorkspace({ moduleId = 'skin-cancer' }: { moduleId?: string }) {
  const [file, setFile] = useState<File | null>(null)
  const [clinical, setClinical] = useState<ClinicalDetails>({ age: null, sex: 'unknown', localization: 'unknown' })
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
      const result = await analysisService.analyze({ cancerType: 'skin', moduleId, file, ...clinical })
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

  if (moduleId === 'skin-cancer') return <CombinedAnalysisWorkspace />

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <ImageUploader file={file} previewUrl={previewUrl} onFileChange={handleFile} disabled={busy} />
        </div>
        <div className="xl:col-span-2">
          <AnalysisControls
            file={file}
            phase={phase}
            onAnalyze={analyze}
            clinical={clinical}
            onClinicalChange={setClinical}
            moduleId={moduleId}
            clinicalEnabled={moduleId !== 'skin-image-analysis'}
          />
        </div>
      </div>
      <AnalysisResults phase={phase} outcome={outcome} error={error} previewUrl={previewUrl} onRetry={analyze} />
    </div>
  )
}

