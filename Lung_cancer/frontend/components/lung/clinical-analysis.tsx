'use client'

import { useState, type FormEvent } from 'react'
import { Activity, Loader2, Play, RotateCcw } from 'lucide-react'
import { Panel, PanelHeader } from '@/components/common/primitives'
import { AnalysisResults } from '@/components/analysis/analysis-results'
import { apiRequest, isApiConfigured } from '@/lib/api-client'
import { getInitialLungClinicalValues, LUNG_CLINICAL_FIELDS } from '@/lib/lung-clinical-fields'
import type { AnalysisOutcome, AnalysisResult } from '@/types'
import type { AnalysisPhase } from '@/components/analysis/analysis-workspace'

const inputClass = 'mt-1 h-10 w-full rounded-xl border border-border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/30'

export function ClinicalAnalysis() {
  const [values, setValues] = useState<Record<string, number>>(
    getInitialLungClinicalValues(),
  )
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [phase, setPhase] = useState<AnalysisPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const busy = phase === 'uploading' || phase === 'processing'

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPhase('processing')
    setError(null)
    setResult(null)
    try {
      const response = await apiRequest<AnalysisResult>('/api/v1/analysis/lung-cancer-clinical', {
        method: 'POST',
        body: { features: values },
      })
      setResult(response)
      setPhase('done')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The analysis could not be completed.')
      setPhase('error')
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {!isApiConfigured && (
        <div className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm text-muted-foreground">
          Backend connect karne ke baad hi clinical estimate chalega. <code>NEXT_PUBLIC_API_URL</code> configure karo.
        </div>
      )}
      <Panel>
        <PanelHeader
          title="Clinical and Risk Factors"
          description="Dataset-based fields bharo. UI score inputs 1–5 tak hain; ye standard medical measurements nahi hain."
          icon={Activity}
        />
        <form id="lung-clinical-form" onSubmit={submit} className="p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {LUNG_CLINICAL_FIELDS.map((field) => (
              <label key={field.key} className="text-sm font-medium">
                {field.label}
                <select
                  className={inputClass}
                  value={values[field.key]}
                  onChange={(event) => setValues((current) => ({ ...current, [field.key]: Number(event.target.value) }))}
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
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={busy || !isApiConfigured}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl brand-gradient px-5 text-sm font-semibold text-white shadow-lg shadow-wc-teal/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? <Loader2 className="size-4 animate-spin" /> : <Play className="size-4" />}
              {busy ? 'Analyzing…' : 'Run Clinical Module'}
            </button>
            <button
              type="button"
              onClick={() => {
                setValues(getInitialLungClinicalValues())
                setResult(null)
                setError(null)
                setPhase('idle')
              }}
              className="inline-flex h-11 items-center gap-2 rounded-xl border border-border px-4 text-sm font-medium hover:bg-muted"
            >
              <RotateCcw className="size-4" /> Reset fields
            </button>
            <span className="text-xs text-muted-foreground">Gender codes used by the model: Male = 1, Female = 2. Scores are limited to 1–5.</span>
          </div>
        </form>
      </Panel>

      <AnalysisResults
        phase={phase}
        outcome={result ? ({ kind: 'result', result } as AnalysisOutcome) : null}
        error={error}
        previewUrl={null}
        onRetry={() => {
          const form = document.querySelector<HTMLFormElement>('#lung-clinical-form')
          form?.requestSubmit()
        }}
        showVisualExplanation={false}
        probabilities={result?.probabilities}
      />
    </div>
  )
}
