'use client'

import { useEffect, useState } from 'react'
import { Activity, BrainCircuit, CheckCircle2, CircleDashed, Layers3, Loader2, ShieldAlert, XCircle } from 'lucide-react'
import { Panel, PanelHeader, inputClass } from '@/components/common/primitives'
import { analyzeBrainClinical } from '@/services/brain-clinical-service'
import { analyzeBrainMultimodal, type BrainMultimodalResult } from '@/services/brain-multimodal-service'
import { analysisService } from '@/services/analysis-service'
import type { AnalysisResult } from '@/types'
import { getMRIScreeningDisplay, runBrainMultimodalPipeline, type BrainClinicalStageResult, type BrainMultimodalPipelineResult, type MRIScreeningResult, type PipelineStageStatus } from '@/services/brain-multimodal-pipeline'
import { BrainMultimodalMRIUploader } from './brain-multimodal-mri-uploader'
import { saveBrainChatContext } from '@/lib/brain-chat-context'

const selectClass = `${inputClass} bg-background`
type PipelineProgress = {
  mri: { status: PipelineStageStatus; message?: string; result?: MRIScreeningResult }
  clinical: { status: PipelineStageStatus; message?: string; result?: BrainClinicalStageResult }
  idh: { status: PipelineStageStatus; message?: string; result?: BrainMultimodalResult }
}

const EMPTY_STAGES: PipelineProgress = {
  mri: { status: 'waiting' as const },
  clinical: { status: 'waiting' as const },
  idh: { status: 'waiting' as const },
}

export function BrainMultimodalWorkspace() {
  const [files, setFiles] = useState<File[]>([])
  const [preview, setPreview] = useState<string | null>(null)
  const [age, setAge] = useState('')
  const [sex, setSex] = useState<'M' | 'F' | ''>('')
  const [grade, setGrade] = useState('')
  const [codeletion, setCodeletion] = useState<'co-deleted' | 'non co-deleted' | ''>('')
  const [mgmt, setMgmt] = useState<'methylated' | 'unmethylated' | ''>('')
  const [pipeline, setPipeline] = useState<BrainMultimodalPipelineResult | null>(null)
  const [stageProgress, setStageProgress] = useState(EMPTY_STAGES)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!files.length) { setPreview(null); return }
    const url = URL.createObjectURL(files[0])
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [files])

  const updateFiles = (next: File[]) => {
    setFiles(next)
    setPipeline(null)
    setStageProgress(EMPTY_STAGES)
    setValidationMessage(null)
  }

  const analyze = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const numericAge = age.trim() ? Number(age) : undefined
    const numericGrade = grade.trim() ? Number(grade) : undefined
    const inputErrors: string[] = []
    if (numericAge !== undefined && (!Number.isFinite(numericAge) || numericAge < 0 || numericAge > 120)) inputErrors.push('Age must be between 0 and 120 to be used by the IDH stage.')
    if (numericGrade !== undefined && ![1, 2, 3, 4].includes(numericGrade)) inputErrors.push('Tumor grade must be 1, 2, 3, or 4.')
    const validAge = numericAge !== undefined && Number.isFinite(numericAge) && numericAge >= 0 && numericAge <= 120 ? numericAge : undefined
    const validGrade = numericGrade !== undefined && [1, 2, 3, 4].includes(numericGrade) ? numericGrade : undefined
    const clinicalInput = validAge !== undefined && validAge >= 5 && validAge <= 78 && sex
      ? { age: validAge, sex, site: undefined }
      : null

    setValidationMessage(inputErrors.length ? inputErrors.join(' ') : null)
    setBusy(true)
    setPipeline(null)
    setStageProgress(EMPTY_STAGES)
    try {
      const outcome = await runBrainMultimodalPipeline({
        files,
        clinical: clinicalInput,
        idh: {
          ageAtImaging: validAge,
          sexAtBirth: sex || undefined,
          tumorGrade: validGrade,
          codeletion1p19q: codeletion || undefined,
          mgmt: mgmt || undefined,
        },
      }, {
        analyzeImage: (file) => analysisService.analyze({ moduleId: 'brain-tumour', file }),
        analyzeClinical: analyzeBrainClinical,
        analyzeIdh: analyzeBrainMultimodal,
      }, (stage, status, message, result) => {
        setStageProgress((current) => {
          const progressStage = <T,>(value: unknown): { status: PipelineStageStatus; message?: string; result?: T } => {
            if (status === 'success' && value !== undefined) return { status, result: value as T }
            if (status === 'success') return { status: 'running', message: 'Result received; preparing this stage.' }
            return { status, message }
          }
          if (stage === 'mri') return { ...current, mri: progressStage<MRIScreeningResult>(result) }
          if (stage === 'clinical') return { ...current, clinical: progressStage<BrainClinicalStageResult>(result) }
          return { ...current, idh: progressStage<BrainMultimodalResult>(result) }
        })
      })
      setPipeline(outcome)
      if (outcome.mri.status === 'success') {
        saveBrainChatContext('brain_multimodal', {
          sequentialAnalysis: {
            mri: { status: outcome.mri.status, prediction: outcome.mri.result.prediction, tumorSlices: outcome.mri.result.tumorSlices, totalSlices: outcome.mri.result.totalSlices, classScores: outcome.mri.result.classScores },
            clinical: outcome.clinical.status === 'success'
              ? { status: 'success', predictedSubtype: outcome.clinical.result.predictedSubtypeLabel, classScores: outcome.clinical.result.classScores }
              : { status: outcome.clinical.status, message: outcome.clinical.message },
            idh: outcome.idh.status === 'success'
              ? { status: 'success', predictedClass: outcome.idh.result.predicted_class, classScores: outcome.idh.result.class_scores }
              : { status: outcome.idh.status, message: outcome.idh.message },
          },
          userProvidedValues: { ageAtImaging: validAge ?? null, sexAtBirth: sex || 'Not provided', tumorGrade: validGrade ?? null, codeletion1p19q: codeletion || 'Not provided', mgmt: mgmt || 'Not provided' },
        })
      }
    } finally {
      setBusy(false)
    }
  }

  return <div className="flex flex-col gap-6">
    <form onSubmit={analyze} className="grid gap-6 xl:grid-cols-5">
      <div className="xl:col-span-3">
        <BrainMultimodalMRIUploader files={files} previewUrl={preview} disabled={busy} onFilesChange={updateFiles} />
      </div>
      <Panel className="flex flex-col xl:col-span-2">
        <PanelHeader title="Clinical information" description="Available values are sent to the existing clinical subtype and IDH models. The clinical model requires age and sex; tumour location is optional." icon={Activity} />
        <div className="flex flex-1 flex-col gap-5 p-5 sm:p-6">
          <div>
            <label htmlFor="brain-multimodal-age" className="mb-1.5 block text-sm font-medium">Age at imaging</label>
            <input id="brain-multimodal-age" type="number" min={0} max={120} step="any" value={age} onChange={(e) => setAge(e.target.value)} className={inputClass} placeholder="Optional age in years" />
          </div>
          <div>
            <label htmlFor="brain-multimodal-sex" className="mb-1.5 block text-sm font-medium">Sex at birth</label>
            <select id="brain-multimodal-sex" value={sex} onChange={(e) => setSex(e.target.value as 'M' | 'F' | '')} className={selectClass}>
              <option value="">Unknown / not provided</option><option value="F">Female</option><option value="M">Male</option>
            </select>
          </div>
          <div>
            <label htmlFor="brain-multimodal-grade" className="mb-1.5 block text-sm font-medium">Tumor grade</label>
            <select id="brain-multimodal-grade" value={grade} onChange={(e) => setGrade(e.target.value)} className={selectClass}>
              <option value="">Unknown / not provided</option><option value="1">Grade 1</option><option value="2">Grade 2</option><option value="3">Grade 3</option><option value="4">Grade 4</option>
            </select>
          </div>
          <div>
            <label htmlFor="brain-multimodal-codeletion" className="mb-1.5 block text-sm font-medium">1p19q codeletion</label>
            <select id="brain-multimodal-codeletion" value={codeletion} onChange={(e) => setCodeletion(e.target.value as typeof codeletion)} className={selectClass}>
              <option value="">Unknown / not provided</option><option value="co-deleted">Co-deleted</option><option value="non co-deleted">Non co-deleted</option>
            </select>
          </div>
          <div>
            <label htmlFor="brain-multimodal-mgmt" className="mb-1.5 block text-sm font-medium">MGMT status</label>
            <select id="brain-multimodal-mgmt" value={mgmt} onChange={(e) => setMgmt(e.target.value as typeof mgmt)} className={selectClass}>
              <option value="">Unknown / not provided</option><option value="methylated">Methylated</option><option value="unmethylated">Unmethylated</option>
            </select>
          </div>
          <p className="mt-auto text-xs leading-5 text-muted-foreground">MRI slices and clinical values should belong to the same patient. Scores are research outputs, not a diagnosis.</p>
          <button type="submit" disabled={busy} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <BrainCircuit className="size-4" />}{busy ? 'Running analysis stages…' : 'Run Multimodal Analysis'}
          </button>
        </div>
      </Panel>
    </form>

    {validationMessage && <div role="status" className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-3 text-sm">{validationMessage} MRI screening and any later stage with usable inputs will still run.</div>}
    {(busy || pipeline) && <PipelineResults pipeline={pipeline} progress={stageProgress} />}
  </div>
}

function PipelineResults({ pipeline, progress }: { pipeline: BrainMultimodalPipelineResult | null; progress: PipelineProgress }) {
  const mri = pipeline?.mri ?? progress.mri
  const clinical = pipeline?.clinical ?? progress.clinical
  const idh = pipeline?.idh ?? progress.idh
  return <Panel aria-live="polite">
    <PanelHeader title="Multimodal Analysis Results" icon={Layers3} />
    <div className="grid gap-4 p-5 sm:p-6">
      <StageCard number="1" title="MRI tumor screening" stage={mri}>
        {mri.status === 'success' && mri.result
          ? <MRIResult result={mri.result} />
          : mri.status === 'success'
            ? <p role="alert" className="text-sm text-destructive">MRI screening completed without a result payload.</p>
            : null}
      </StageCard>
      <StageCard number="2" title="Clinical glioma subtype" stage={clinical}>
        {clinical.status === 'success' && clinical.result
          ? <ClinicalResult result={clinical.result} />
          : clinical.status === 'success'
            ? <p role="alert" className="text-sm text-destructive">Clinical inference completed without a subtype result. Run this stage again.</p>
            : null}
      </StageCard>
      <StageCard number="3" title="IDH molecular classification" stage={idh}>
        {idh.status === 'success' && idh.result
          ? <IDHResult result={idh.result} />
          : idh.status === 'success'
            ? <p role="alert" className="text-sm text-destructive">IDH inference completed without a result payload.</p>
            : null}
      </StageCard>
    </div>
  </Panel>
}

function StageCard({ number, title, stage, children }: { number: string; title: string; stage: { status: PipelineStageStatus; message?: string }; children: React.ReactNode }) {
  const message = stage.message ?? (stage.status === 'waiting' ? 'Not run yet.' : undefined)
  return <section className="rounded-xl border border-border p-4 sm:p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-sm font-semibold">Stage {number} · {title}</h3><StageBadge status={stage.status} /></div>
    {message && <p className="mt-3 text-sm leading-6 text-muted-foreground">{message}</p>}
    {children && <div className="mt-4 border-t border-border pt-4">{children}</div>}
  </section>
}

function StageBadge({ status }: { status: PipelineStageStatus }) {
  const style = status === 'success' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300' : status === 'failed' ? 'bg-red-500/10 text-red-700 dark:text-red-300' : status === 'running' ? 'bg-wc-cyan/10 text-wc-cyan' : 'bg-muted text-muted-foreground'
  const Icon = status === 'success' ? CheckCircle2 : status === 'failed' ? XCircle : status === 'running' ? Loader2 : CircleDashed
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${style}`}><Icon className={`size-3.5 ${status === 'running' ? 'animate-spin' : ''}`} />{status}</span>
}

function MRIResult({ result }: { result: MRIScreeningResult }) {
  const display = getMRIScreeningDisplay(result)
  if (!display) {
    return <p role="alert" className="text-sm text-destructive">MRI screening returned no predicted class.</p>
  }
  return <div className="grid gap-4 lg:grid-cols-2">
    <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Screening branch</p><p className="mt-1 text-xl font-semibold">{display.screeningLabel}</p><p className="mt-1 text-sm text-muted-foreground">Selected actual Brain Image class: <strong className="text-foreground">{display.prediction}</strong></p><p className="mt-1 text-xs leading-5 text-muted-foreground">{result.tumorSlices} of {result.totalSlices} uploaded slices predicted a tumor class. Showing the slice with the highest actual predicted-class score: {result.selectedFileName}.</p>{!display.previewAvailable && <p className="mt-2 text-xs text-muted-foreground">Selected slice preview unavailable; the model prediction remains available.</p>}</div>
    {display.classScores
      ? <ScoreList title="Selected slice model class scores" scores={display.classScores} predicted={display.classification} />
      : <p className="rounded-lg bg-muted/30 p-3 text-sm text-muted-foreground">Class scores are unavailable for this result.</p>}
  </div>
}

function ClinicalResult({ result }: { result: BrainClinicalStageResult }) {
  if (!result || typeof result !== 'object') {
    return <p role="alert" className="text-sm text-destructive">Clinical inference completed without a result payload. Run this stage again.</p>
  }
  const subtype = result.predictedSubtypeLabel?.trim() || result.predictedSubtype?.trim()
  if (!subtype) {
    return <p role="alert" className="text-sm text-destructive">Clinical inference returned no subtype label.</p>
  }
  return <div className="grid gap-4 lg:grid-cols-2">
    <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Predicted glioma subtype</p><p className="mt-1 text-xl font-semibold">{subtype}</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Existing IPD-Brain clinical model · {result.scoreType}. Its training cohort contains glioma cases; results are not validated for other MRI tumor classes.</p></div>
    {result.classScores && Object.keys(result.classScores).length
      ? <ScoreList title="Clinical subtype class scores" scores={result.classScores} predicted={result.predictedSubtype} />
      : <p className="rounded-lg bg-muted/30 p-3 text-sm text-muted-foreground">The subtype was returned, but this response did not include class scores.</p>}
  </div>
}

function IDHResult({ result }: { result: BrainMultimodalResult }) {
  if (!result || typeof result !== 'object') {
    return <p role="alert" className="text-sm text-destructive">The IDH analysis completed without a result payload. Restart the Brain API and run the analysis again.</p>
  }
  return <div className="grid gap-4 lg:grid-cols-2">
    <div><p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Predicted IDH class</p><p className="mt-1 text-xl font-semibold capitalize">{result.predicted_class}</p><p className="mt-1 text-xs text-muted-foreground">Existing UTSW MRI + clinical model · {result.n_slices_used} slice{result.n_slices_used === 1 ? '' : 's'} used.</p><p className="mt-2 break-all text-xs text-muted-foreground">{result.score_interpretation} · Checkpoint: {result.checkpoint}</p></div>
    <ScoreList title="IDH class scores" scores={result.class_scores} predicted={result.predicted_class} />
  </div>
}

function ScoreList({ title, scores, predicted }: { title: string; scores: Record<string, number>; predicted: string }) {
  return <div className="rounded-lg bg-muted/30 p-3"><h4 className="text-xs font-semibold">{title}</h4><div className="mt-3 space-y-2">{Object.entries(scores).map(([label, score]) => <div key={label} className="flex justify-between gap-3 text-xs"><span className={label.toLowerCase() === predicted.toLowerCase() ? 'font-semibold text-foreground' : 'text-muted-foreground'}>{label}{label.toLowerCase() === predicted.toLowerCase() ? ' · predicted' : ''}</span><span className="font-mono">{(score * 100).toFixed(1)}%</span></div>)}</div><p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground"><ShieldAlert className="size-3" />Model scores are not calibrated probabilities.</p></div>
}
