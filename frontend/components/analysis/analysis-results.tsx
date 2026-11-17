'use client'

/* eslint-disable @next/next/no-img-element -- previews are local object URLs */
import { useRouter } from 'next/navigation'
import { AlertTriangle, BrainCircuit, Clock, Cpu, Flame, Gauge, Hourglass, Loader2, RotateCcw, Tag } from 'lucide-react'
import { Badge, EmptyState, Panel, PanelHeader } from '@/components/common/primitives'
import { PENDING_MODEL_INFO } from '@/lib/demo-data'
import type { AnalysisOutcome, ModelInfo } from '@/types'
import type { AnalysisPhase } from './analysis-workspace'

interface Props {
  phase: AnalysisPhase
  outcome: AnalysisOutcome | null
  error: string | null
  previewUrl: string | null
  onRetry: () => void
  title?: string
  description?: string
}

export function AnalysisResults({ phase, outcome, error, previewUrl, onRetry, title = 'Research Results', description = 'Model output, explanation and metadata.' }: Props) {
  const router = useRouter()
  const result = outcome?.kind === 'result' ? outcome.result : null
  const imageOnlyResult = result?.moduleId === 'skin-image-analysis'
  const inputImageUrl = result?.originalImageUrl ?? previewUrl
  const pending = outcome?.kind === 'pending'
  const busy = phase === 'uploading' || phase === 'processing'
  const model: ModelInfo = result?.model ?? PENDING_MODEL_INFO

  return (
    <Panel aria-live="polite">
      <PanelHeader
        title={title}
        description={description}
        icon={BrainCircuit}
        action={result?.isDemo ? <Badge tone="violet">Demo output</Badge> : pending ? <Badge tone="amber">Integration pending</Badge> : undefined}
      />
      <div className="p-5 sm:p-6">
        {busy && (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <span className="relative flex size-14 items-center justify-center">
              <span className="absolute inset-0 animate-ping rounded-full bg-wc-cyan/20" />
              <Loader2 className="size-8 animate-spin text-wc-cyan" aria-hidden />
            </span>
            <p className="text-sm font-semibold">{phase === 'uploading' ? 'Uploading imageâ€¦' : 'Processing analysisâ€¦'}</p>
            <p className="text-xs text-muted-foreground">This may take a moment.</p>
          </div>
        )}

        {phase === 'error' && error && (
          <EmptyState
            icon={AlertTriangle}
            title="Analysis could not be completed"
            description={error}
            className="border-red-500/30 bg-red-500/5"
            action={
              <button type="button" onClick={onRetry} className="inline-flex h-9 items-center gap-2 rounded-xl border border-border bg-card px-4 text-sm font-medium hover:bg-muted">
                <RotateCcw className="size-4" aria-hidden /> Try again
              </button>
            }
          />
        )}

        {phase === 'idle' && <EmptyState icon={Hourglass} title="No analysis yet" description="Upload an image and select Analyze Image to view research output here." />}

        {phase === 'done' && (pending || result) && (
          <div className="flex flex-col gap-5">
            {pending && (
              <div className="flex items-start gap-3 rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4">
                <Cpu className="mt-0.5 size-5 shrink-0 text-wc-amber" aria-hidden />
                <div>
                  <p className="text-sm font-semibold">Model integration pending</p>
                  <p className="mt-0.5 text-sm text-muted-foreground">{outcome.message}</p>
                </div>
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-3">
              <ResultTile icon={Tag} label="Model prediction" value={result ? result.prediction : 'Pending'} muted={!result} />
              <ResultTile
                icon={Gauge}
                label="Confidence score"
                value={result && !result.isDemo ? `${(result.confidence * 100).toFixed(1)}%` : 'â€”'}
                hint={result?.isDemo ? 'Not shown in demo mode' : !result ? 'Pending' : undefined}
                muted={!result || result.isDemo}
              />
              <ResultTile icon={BrainCircuit} label="Classification output" value={result ? result.classification : 'Pending'} muted={!result} />
            </div>

            {result && !result.isDemo && (
              <>
                {result.patient && <div className="rounded-xl border border-border bg-elevated p-4">
                  <p className="text-sm font-semibold">Submitted clinical information</p>
                  <dl className="mt-2 grid gap-3 text-sm sm:grid-cols-3">
                    <Meta label="Age" value={result.patient.age == null ? 'Not provided' : `${result.patient.age} years`} />
                    <Meta label="Sex" value={result.patient.sex === 'unknown' ? 'Not provided' : result.patient.sex} />
                    <Meta label="Lesion location" value={result.patient.localization === 'unknown' ? 'Not provided' : result.patient.localization} />
                  </dl>
                </div>}
                {result.probabilities && <div className="grid gap-4 xl:grid-cols-3">
                  <ProbabilityPanel title={imageOnlyResult ? 'Image-only ResNet-18' : 'Image + clinical fusion'} values={result.probabilities} names={result.classNames ?? {}} />
                  {result.imageOnlyProbabilities && <ProbabilityPanel title="Image-only ResNet-18" values={result.imageOnlyProbabilities} names={result.classNames ?? {}} />}
                  {result.clinicalOnlyProbabilities && <ProbabilityPanel title="Clinical-only MLP" values={result.clinicalOnlyProbabilities} names={result.classNames ?? {}} />}
                </div>}
                <button type="button" onClick={() => router.push(`/reports?analysisId=${encodeURIComponent(result.analysisId)}`)} className="inline-flex h-10 items-center justify-center self-start rounded-xl border border-border bg-card px-4 text-sm font-semibold hover:bg-muted">
                  View detailed research report
                </button>
              </>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-border p-4">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Flame className="size-4 text-wc-pink" aria-hidden /> Visual explanation / heatmap
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <figure className="flex flex-col gap-1.5">
                    <div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-muted">
                      {inputImageUrl && <img src={inputImageUrl} alt="Uploaded image" className={imageOnlyResult ? 'size-full object-contain' : 'size-full object-cover'} />}
                    </div>
                    <figcaption className="text-xs text-muted-foreground">Input image</figcaption>
                  </figure>
                  <figure className="flex flex-col gap-1.5">
                    <div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg border border-dashed border-border bg-muted/50 p-3 text-center">
                      {result?.heatmapUrl ? (
                        <img src={result.heatmapUrl} alt="Model attention heatmap" className="size-full object-cover" />
                      ) : (
                        <span className="text-xs text-muted-foreground">Heatmap available after model integration (e.g. Grad-CAM)</span>
                      )}
                    </div>
                    <figcaption className="text-xs text-muted-foreground">Explanation map</figcaption>
                  </figure>
                </div>
              </div>

              <div className="rounded-xl border border-border p-4">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Cpu className="size-4 text-wc-violet" aria-hidden /> Model information
                </p>
                <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-2.5 text-sm sm:grid-cols-2">
                  <Meta label="Model" value={model.name} />
                  <Meta label="Version" value={model.version} />
                  <Meta label="Architecture" value={model.architecture} />
                  <Meta label="Dataset" value={model.dataset} />
                  <Meta label="Analysis ID" value={result?.analysisId ?? 'â€”'} mono />
                  <Meta
                    label="Analysis timestamp"
                    value={new Date(result?.createdAt ?? Date.now()).toLocaleString()}
                    icon={<Clock className="size-3" aria-hidden />}
                  />
                </dl>
              </div>
            </div>
          </div>
        )}
      </div>
    </Panel>
  )
}

function ResultTile({ icon: Icon, label, value, hint, muted }: { icon: typeof Tag; label: string; value: string; hint?: string; muted?: boolean }) {
  return (
    <div className="rounded-xl border border-border bg-elevated p-4">
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" aria-hidden /> {label}
      </p>
      <p className={muted ? 'mt-2 text-lg font-semibold text-muted-foreground' : 'mt-2 text-lg font-semibold'}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  )
}

function Meta({ label, value, mono, icon }: { label: string; value: string; mono?: boolean; icon?: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="flex items-center gap-1 text-xs text-muted-foreground">
        {icon}
        {label}
      </dt>
      <dd className={mono ? 'truncate font-mono text-sm font-medium' : 'truncate font-medium'} title={value}>
        {value}
      </dd>
    </div>
  )
}

function ProbabilityPanel({ title, values, names }: { title: string; values: Record<string, number>; names: Record<string, string> }) {
  return <div className="rounded-xl border border-border p-4">
    <p className="text-sm font-semibold">{title}</p>
    <div className="mt-3 flex flex-col gap-3">{Object.entries(values).map(([code, value]) => <div key={code}>
      <div className="mb-1 flex justify-between gap-2 text-xs"><span className="font-medium">{names[code] || code} <span className="text-muted-foreground">({code})</span></span><span className="shrink-0 text-muted-foreground">{(value * 100).toFixed(2)}%</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-turquoise" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>
    </div>)}</div>
  </div>
}

