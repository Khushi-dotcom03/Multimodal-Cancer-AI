'use client'

/* eslint-disable @next/next/no-img-element -- uploaded images and API data URLs */
import { useEffect, useState } from 'react'
import { BrainCircuit, Flame, Loader2 } from 'lucide-react'
import { analysisService } from '@/services/analysis-service'
import type { AnalysisResult } from '@/types'
import { BrainMRIUploader } from './brain-mri-uploader'

const DISCLAIMER = 'This is an AI-based research and educational classification result. It is not a medical diagnosis and must not replace professional radiological evaluation.'

export function BrainImageWorkspace() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!file) { setPreview(null); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const analyze = async () => {
    if (!file) return
    setBusy(true); setError(null); setResult(null)
    try {
      const outcome = await analysisService.analyze({ moduleId: 'brain-tumour', file })
      if (outcome.kind !== 'result' || outcome.result.isDemo) throw new Error('A real model result was not returned by the backend.')
      setResult(outcome.result)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Brain MRI analysis failed. Please try again.')
    } finally { setBusy(false) }
  }

  const scores = result?.classScores
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-6 xl:grid-cols-5">
        <div className="xl:col-span-3">
          <BrainMRIUploader file={file} previewUrl={preview} onFileChange={(next) => { setFile(next); setResult(null); setError(null) }} disabled={busy} />
        </div>
        <div className="flex flex-col justify-between gap-4 rounded-2xl border border-border bg-card p-5 sm:p-6 xl:col-span-2">
          <div>
            <div className="flex items-center gap-2 text-sm font-semibold"><BrainCircuit className="size-4 text-wc-violet" /> Image-based analysis</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">The selected image is processed by the pretrained MIND EfficientNet-B0 checkpoint. No clinical information is requested.</p>
          </div>
          <button type="button" onClick={analyze} disabled={!file || busy} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition-opacity disabled:cursor-not-allowed disabled:opacity-50">
            {busy && <Loader2 className="size-4 animate-spin" />}{busy ? 'Uploading image and analyzing…' : 'Analyze Image'}
          </button>
        </div>
      </div>

      {error && <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-700 dark:text-red-300"><strong>Analysis unavailable.</strong> {error}</div>}
      {busy && <div aria-live="polite" className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-card p-10 text-sm font-medium"><Loader2 className="size-5 animate-spin text-wc-cyan" /> Running brain MRI inference…</div>}

      {result && <section aria-live="polite" className="flex flex-col gap-5 rounded-2xl border border-border bg-card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-wc-violet">Predicted class</p><h2 className="mt-1 text-2xl font-bold">{result.prediction}</h2><p className="mt-1 text-sm text-muted-foreground">Model confidence score: <span className="font-semibold text-foreground">{(result.confidence * 100).toFixed(1)}%</span> · uncalibrated softmax score</p></div><span className="rounded-full bg-wc-violet/10 px-3 py-1 text-xs font-semibold text-wc-violet">{result.model.architecture}</span></div>

        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-xl border border-border p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold"><BrainCircuit className="size-4" /> Class scores</h3>
            <p className="mt-1 text-xs text-muted-foreground">Softmax model scores; not calibrated probabilities.</p>
            <div className="mt-4 space-y-3">{Object.entries(scores ?? {}).map(([name, value]) => <div key={name}>
              <div className="mb-1 flex justify-between gap-3 text-sm"><span className={name === result.classification ? 'font-semibold' : 'text-muted-foreground'}>{name}{name === result.classification ? ' · highest' : ''}</span><span className="font-mono">{(value * 100).toFixed(1)}%</span></div>
              <div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${name === result.classification ? 'bg-wc-violet' : 'bg-wc-cyan/60'}`} style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>
            </div>)}</div>
          </div>
          <div className="rounded-xl border border-border p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold"><Flame className="size-4 text-wc-pink" /> MRI visualization</h3>
            <div className="mt-3 grid grid-cols-3 gap-2">{[
              { label: 'Original', src: preview },
              { label: 'Grad-CAM', src: result.gradcam?.heatmap },
              { label: 'Overlay', src: result.gradcam?.overlay ?? result.heatmapUrl },
            ].map(({ label, src }) => <figure key={label} className="min-w-0"><div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-muted">{src ? <img src={src} alt={`${label} brain MRI`} className="size-full object-contain" /> : <span className="px-2 text-center text-xs text-muted-foreground">{label === 'Original' ? 'Image unavailable' : 'Grad-CAM unavailable'}</span>}</div><figcaption className="mt-1.5 text-center text-xs text-muted-foreground">{label}</figcaption></figure>
            )}</div>
            {!result.gradcam?.available && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Grad-CAM could not be generated for this image. The prediction is still available.</p>}
          </div>
        </div>
        <dl className="grid gap-3 rounded-xl bg-muted/50 p-4 text-sm sm:grid-cols-3"><div><dt className="text-xs text-muted-foreground">Analysis ID</dt><dd className="mt-1 break-all font-mono">{result.analysisId}</dd></div><div><dt className="text-xs text-muted-foreground">Model</dt><dd className="mt-1 font-medium">{result.model.name}</dd></div><div><dt className="text-xs text-muted-foreground">Inference status</dt><dd className="mt-1 font-medium">{result.inferenceStatus ?? 'completed'}</dd></div></dl>
        <p className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6">{result.disclaimer ?? DISCLAIMER}</p>
      </section>}
    </div>
  )
}
