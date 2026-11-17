'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { Activity, Loader2, Play, RotateCcw } from 'lucide-react'
import { AnalysisResults } from '@/components/analysis/analysis-results'
import { ImageUploader } from '@/components/analysis/image-uploader'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { isApiConfigured } from '@/lib/api-client'
import { getInitialLungClinicalValues, LUNG_CLINICAL_FIELDS } from '@/lib/lung-clinical-fields'
import type { AnalysisOutcome, AnalysisResult } from '@/types'
import type { AnalysisPhase } from '@/components/analysis/analysis-workspace'

const inputClass = 'mt-1 h-10 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/30'

export function FusionAnalysis() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [values, setValues] = useState<Record<string, number>>(getInitialLungClinicalValues())
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [phase, setPhase] = useState<AnalysisPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const busy = phase === 'uploading' || phase === 'processing'

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const analyze = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault()
    if (!file) return
    setPhase('processing')
    setError(null)
    setResult(null)
    const body = new FormData()
    body.append('file', file)
    body.append('features', JSON.stringify(values))
    try {
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 300_000)
      const response = await fetch('/api/proxy/lung-cancer-fusion', {
        method: 'POST',
        body,
        signal: controller.signal,
      })
      window.clearTimeout(timeout)
      if (!response.ok) {
        const data = await response.json().catch(() => null)
        throw new Error(data?.detail || `Request failed with status ${response.status}`)
      }
      setResult(await response.json() as AnalysisResult)
      setPhase('done')
    } catch (reason) {
      setError(reason instanceof DOMException && reason.name === 'AbortError'
        ? 'The analysis timed out. Please try again.'
        : reason instanceof Error ? reason.message : 'The combined analysis could not be completed.')
      setPhase('error')
    }
  }

  const reset = () => {
    setFile(null)
    setValues(getInitialLungClinicalValues())
    setResult(null)
    setError(null)
    setPhase('idle')
  }

  return (
    <div className="flex flex-col gap-6">
      {!isApiConfigured && (
        <div className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm text-muted-foreground">
          Backend connect karne ke baad hi dono models chalenge. <code>NEXT_PUBLIC_API_URL</code> configure karo.
        </div>
      )}
      <form onSubmit={analyze} className="grid gap-6 xl:grid-cols-2">
        <ImageUploader
          file={file}
          previewUrl={previewUrl}
          onFileChange={(next) => {
            setFile(next)
            setResult(null)
            setError(null)
            setPhase('idle')
          }}
          disabled={busy}
          title="CT Slice Upload"
          description="Upload one 2D CT slice image (JPG, JPEG, or PNG)."
        />
        <Panel>
          <PanelHeader
            title="Clinical Inputs"
            description="Use the same fields and score limits as Module 2."
            icon={Activity}
          />
          <div className="p-5 sm:p-6">
            <div className="grid gap-3 sm:grid-cols-2">
              {LUNG_CLINICAL_FIELDS.map((field) => (
                <label key={field.key} className="text-sm font-medium">
                  {field.label}
                  <select
                    className={inputClass}
                    value={values[field.key]}
                    onChange={(event) => setValues((current) => ({ ...current, [field.key]: Number(event.target.value) }))}
                    disabled={busy}
                  >
                    {field.key === 'Gender' ? (
                      <>
                        <option value={1}>Male</option>
                        <option value={2}>Female</option>
                      </>
                    ) : (
                      Array.from({ length: field.max - field.min + 1 }, (_, index) => field.min + index).map((value) => (
                        <option key={value} value={value}>{value}</option>
                      ))
                    )}
                  </select>
                </label>
              ))}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
              Image and clinical models run independently. Dataset score inputs are limited to 1–5; they are not standard medical measurements.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={!file || busy || !isApiConfigured}
                className="inline-flex h-11 items-center justify-center gap-2 rounded-xl brand-gradient px-5 text-sm font-semibold text-white shadow-lg shadow-wc-teal/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
                {busy ? 'Analyzing…' : 'Run Image + Clinical'}
              </button>
              <button
                type="button"
                onClick={reset}
                disabled={busy}
                className="inline-flex h-11 items-center gap-2 rounded-xl border border-border px-4 text-sm font-medium hover:bg-muted disabled:opacity-50"
              >
                <RotateCcw className="size-4" /> Reset
              </button>
            </div>
          </div>
        </Panel>
      </form>
      <AnalysisResults
        phase={phase}
        outcome={result ? ({ kind: 'result', result } as AnalysisOutcome) : null}
        error={error}
        previewUrl={previewUrl}
        onRetry={() => { void analyze() }}
        showVisualExplanation={false}
        emptyDescription="Upload a CT slice, enter clinical values, then select Run Image + Clinical to view both outputs."
      />
    </div>
  )
}
