'use client'

import { Check, Cpu, FlaskConical, Loader2, Microscope, Play, SlidersHorizontal } from 'lucide-react'
import { Badge, Panel, PanelHeader, Switch } from '@/components/common/primitives'
import { isApiConfigured } from '@/lib/api-client'
import { cn } from '@/lib/utils'
import type { AnalysisPhase } from './analysis-workspace'

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const STEPS: { id: AnalysisPhase; label: string }[] = [
  { id: 'uploading', label: 'Uploading image' },
  { id: 'processing', label: 'Running model' },
  { id: 'done', label: 'Results ready' },
]

interface Props {
  file: File | null
  phase: AnalysisPhase
  onAnalyze: () => void
  demoMode: boolean
  onDemoModeChange: (value: boolean) => void
}

export function AnalysisControls({ file, phase, onAnalyze, demoMode, onDemoModeChange }: Props) {
  const busy = phase === 'uploading' || phase === 'processing'
  const stepIndex = STEPS.findIndex((s) => s.id === phase)

  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader title="Analysis Controls" description="Configure and run the analysis." icon={SlidersHorizontal} />
      <div className="flex flex-1 flex-col gap-5 p-5 sm:p-6">
        <div className="flex items-center gap-3 rounded-xl border border-border bg-elevated p-3">
          <span className="flex size-10 items-center justify-center rounded-xl bg-wc-turquoise/12 text-wc-teal dark:text-wc-turquoise">
            <Microscope className="size-5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-xs text-muted-foreground">Selected module</p>
            <p className="text-sm font-semibold">Skin Cancer</p>
          </div>
          <Badge tone="emerald">Prototype</Badge>
        </div>

        <div>
          <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">Uploaded image</p>
          {file ? (
            <dl className="mt-2 grid grid-cols-3 gap-2 text-sm">
              <div className="col-span-3 rounded-lg bg-muted px-3 py-2">
                <dt className="text-xs text-muted-foreground">File name</dt>
                <dd className="truncate font-medium" title={file.name}>
                  {file.name}
                </dd>
              </div>
              <div className="rounded-lg bg-muted px-3 py-2">
                <dt className="text-xs text-muted-foreground">Format</dt>
                <dd className="font-mono font-medium uppercase">{file.type.split('/')[1]}</dd>
              </div>
              <div className="col-span-2 rounded-lg bg-muted px-3 py-2">
                <dt className="text-xs text-muted-foreground">Size</dt>
                <dd className="font-mono font-medium">{formatBytes(file.size)}</dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 rounded-lg bg-muted px-3 py-2.5 text-sm text-muted-foreground">No image selected yet.</p>
          )}
        </div>

        <div className="flex items-center justify-between gap-3 rounded-xl border border-border p-3">
          <div className="flex items-start gap-2.5">
            <FlaskConical className="mt-0.5 size-4 text-wc-violet" aria-hidden />
            <div>
              <label htmlFor="demo-mode" className="text-sm font-medium">
                Demonstration mode
              </label>
              <p className="text-xs text-muted-foreground">Show labelled placeholder output for UI testing.</p>
            </div>
          </div>
          <Switch id="demo-mode" checked={demoMode} onCheckedChange={onDemoModeChange} label="Demonstration mode" />
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Cpu className="size-3.5" aria-hidden />
          Backend: {isApiConfigured ? <span className="font-medium text-emerald-600 dark:text-emerald-400">configured</span> : <span className="font-medium text-amber-600 dark:text-amber-400">not connected</span>}
        </div>

        <div className="mt-auto flex flex-col gap-4">
          {phase !== 'idle' && phase !== 'error' && (
            <ol className="flex flex-col gap-2" aria-label="Processing status">
              {STEPS.map((s, i) => {
                const complete = i < stepIndex || phase === 'done'
                const current = i === stepIndex && busy
                return (
                  <li key={s.id} className="flex items-center gap-2.5 text-sm">
                    <span
                      className={cn(
                        'flex size-5 items-center justify-center rounded-full',
                        complete ? 'bg-wc-emerald text-white' : current ? 'bg-wc-cyan/15 text-wc-cyan' : 'bg-muted text-muted-foreground',
                      )}
                    >
                      {complete ? <Check className="size-3" /> : current ? <Loader2 className="size-3 animate-spin" /> : <span className="size-1.5 rounded-full bg-current" />}
                    </span>
                    <span className={cn(complete || current ? 'text-foreground' : 'text-muted-foreground')}>{s.label}</span>
                  </li>
                )
              })}
            </ol>
          )}
          <button
            type="button"
            onClick={onAnalyze}
            disabled={!file || busy}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl brand-gradient px-5 text-sm font-semibold text-white shadow-lg shadow-wc-teal/20 transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
          >
            {busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Play className="size-4" aria-hidden />}
            {busy ? 'Analyzing…' : 'Analyze Image'}
          </button>
        </div>
      </div>
    </Panel>
  )
}
