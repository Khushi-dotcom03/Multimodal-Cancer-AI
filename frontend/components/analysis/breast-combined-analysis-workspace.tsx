'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { Activity, AlertCircle, FlaskConical, Layers3, Loader2, ScanSearch } from 'lucide-react'
import { ImageUploader } from '@/components/analysis/image-uploader'
import { Badge, inputClass, Panel, PanelHeader } from '@/components/common/primitives'

type ImageResult = {
  status: string
  prediction: string | null
  confidence: number | null
  probabilities: Record<string, number | null>
  inferenceStatus: string
  validatorProbability: number | null
  message: string
  disclaimer: string
}
type ClinicalResult = {
  status: string
  predictedGrade: number | null
  predictedGradeLabel: string | null
  gradeScores?: { grade: number; voteShare: number }[]
  message: string
  disclaimer: string
}
type Module3Result = {
  status: string
  imageResult: ImageResult
  clinicalResult: ClinicalResult
  fusionResult: { status: 'unavailable'; prediction: null; score: null; reason: string }
  disclaimer: string
}
type ClinicalInputs = { age: string; tumorSize: string; er: string; pr: string; her2: string }

const INITIAL_INPUTS: ClinicalInputs = { age: '', tumorSize: '', er: '', pr: '', her2: '' }
const percent = (value: number | null | undefined) => typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'Unavailable'

function getImageOnlyScores(probabilities: Record<string, number | null> | undefined) {
  const normal = probabilities?.Normal
  const benign = probabilities?.Benign
  const malignant = probabilities?.Malignant
  if ([normal, benign, malignant].some((value) => typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1)) return null
  // This is only a regrouping of Module 1 class outputs, not a multimodal or calibrated cancer probability.
  return { cancerLike: malignant as number, nonCancerLike: (normal as number) + (benign as number) }
}

function ProbabilityBar({ label, value }: { label: string; value: number | null }) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) return null
  return <div className="space-y-1.5"><div className="flex justify-between gap-3 text-sm"><span>{label}</span><span className="tabular-nums">{percent(value)}</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-turquoise" style={{ width: percent(value) }} /></div></div>
}

export function BreastCombinedAnalysisWorkspace() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [clinical, setClinical] = useState<ClinicalInputs>(INITIAL_INPUTS)
  const [result, setResult] = useState<Module3Result | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!file) { setPreviewUrl(null); return }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const analyze = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) { setError('Upload a breast ultrasound image.'); return }
    setBusy(true); setError(null); setResult(null)
    const body = new FormData()
    body.append('file', file)
    body.append('features', JSON.stringify({
      'Age at Diagnosis': Number(clinical.age),
      'Tumor Size': Number(clinical.tumorSize),
      'ER Status': clinical.er,
      'PR Status': clinical.pr,
      'HER2 Status': clinical.her2,
    }))
    try {
      const response = await fetch('/api/proxy/breast-cancer-fusion', { method: 'POST', body })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload?.detail === 'string' ? payload.detail : `Request failed with status ${response.status}`)
      setResult(payload as Module3Result)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Combined analysis request failed.')
    } finally { setBusy(false) }
  }

  const changeFile = (next: File | null) => { setFile(next); setResult(null) }

  return <div className="flex flex-col gap-6">
    <form onSubmit={analyze} className="grid gap-6 xl:grid-cols-2">
      <div className="flex flex-col gap-4">
        <ImageUploader file={file} previewUrl={previewUrl} onFileChange={changeFile} disabled={busy} title="Ultrasound Image" description="Upload a breast ultrasound image (JPG, JPEG, or PNG). Module 1's existing validation and inference pipeline will be used." />
        {error && <p role="alert" className="flex gap-2 rounded-xl border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700 dark:text-red-300"><AlertCircle className="size-4 shrink-0" />{error}</p>}
      </div>

      <Panel className="flex flex-col">
        <PanelHeader title="Clinical inputs" description="Enter the same five fields used by Module 2. Its existing preprocessing and grade model will be used unchanged." icon={Activity} />
        <div className="flex flex-1 flex-col gap-4 p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <label htmlFor="m3-age" className="text-sm font-medium">Age at Diagnosis<input id="m3-age" className={`${inputClass} mt-1`} type="number" min={0} max={120} step={1} required value={clinical.age} disabled={busy} onChange={(event) => setClinical((current) => ({ ...current, age: event.target.value }))} /></label>
            <label htmlFor="m3-tumor-size" className="text-sm font-medium">Tumor Size (mm)<input id="m3-tumor-size" className={`${inputClass} mt-1`} type="number" min={0} step="0.1" required value={clinical.tumorSize} disabled={busy} onChange={(event) => setClinical((current) => ({ ...current, tumorSize: event.target.value }))} /><span className="mt-1 block text-xs font-normal text-muted-foreground">Enter millimetres (for example, 20 mm; convert 2 cm to 20 mm).</span></label>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {([['er', 'ER Status'], ['pr', 'PR Status'], ['her2', 'HER2 Status']] as const).map(([key, label]) => <label key={key} htmlFor={`m3-${key}`} className="text-sm font-medium">{label}<select id={`m3-${key}`} className={`${inputClass} mt-1`} required value={clinical[key]} disabled={busy} onChange={(event) => setClinical((current) => ({ ...current, [key]: event.target.value }))}><option value="">Choose</option><option>Positive</option><option>Negative</option></select></label>)}
          </div>
          <button type="submit" disabled={busy} className="mt-auto inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-wait disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Layers3 className="size-4" aria-hidden />}{busy ? 'Running independent analyses…' : 'Run both analyses'}</button>
          <p className="text-xs leading-relaxed text-muted-foreground">The image and clinical pipelines run independently. No combined prediction is produced.</p>
        </div>
      </Panel>
    </form>

    <Panel>
      <PanelHeader title="Research Results" description="Independent Module 1 and Module 2 outputs." icon={FlaskConical} />
      <div className="space-y-5 p-5 sm:p-6">
          {result && <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs text-muted-foreground">Combined prediction</p><p className="mt-1 text-lg font-semibold">Unavailable</p></div>
            <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs text-muted-foreground">Fusion score</p><p className="mt-1 text-lg font-semibold">Not calculated</p></div>
            <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs text-muted-foreground">Module 2 clinical output</p><p className="mt-1 text-lg font-semibold">{result.clinicalResult.predictedGradeLabel ?? 'Unavailable'}</p></div>
          </div>}
        <div className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-relaxed text-muted-foreground"><strong className="text-foreground">Fusion result unavailable.</strong> The available image dataset is not paired with all five Module 2 inputs, and no compatible patient-linked training cohort has been verified. Tumor grade is not a cancer probability. A combined cancer prediction or score would be unsupported.</div>
        {!result ? <p className="rounded-xl border border-border bg-muted/40 p-4 text-sm text-muted-foreground">Submit the ultrasound image and five clinical inputs to view both independent model outputs.</p> : <div className="grid gap-4 lg:grid-cols-2">
          <section className="space-y-4 rounded-xl border border-border p-4" aria-live="polite">
            <div className="flex items-center gap-2 text-sm font-semibold"><ScanSearch className="size-4 text-wc-teal" />Module 1 · Ultrasound image output</div>
            <div className="flex flex-wrap items-center gap-2"><Badge tone={result.imageResult.status === 'success' ? 'teal' : 'amber'}>{result.imageResult.status}</Badge><span className="font-medium">{result.imageResult.prediction ?? 'No prediction'}</span></div>
            <p className="text-sm text-muted-foreground">Model confidence: {percent(result.imageResult.confidence)}</p>
            <div className="space-y-3">{(['Normal', 'Benign', 'Malignant'] as const).map((name) => <ProbabilityBar key={name} label={name} value={result.imageResult.probabilities?.[name] ?? null} />)}</div>
            {result.imageResult.validatorProbability != null && <p className="text-xs text-muted-foreground">Image validator output: {percent(result.imageResult.validatorProbability)}</p>}
            {result.imageResult.message && <p className="text-xs text-muted-foreground">{result.imageResult.message}</p>}
          </section>
          <section className="space-y-4 rounded-xl border border-border p-4" aria-live="polite">
            <div className="flex items-center gap-2 text-sm font-semibold"><Activity className="size-4 text-wc-teal" />Module 2 · Clinical grade output</div>
            <div className="flex flex-wrap items-center gap-2"><Badge tone={result.clinicalResult.status === 'success' ? 'teal' : 'amber'}>{result.clinicalResult.status}</Badge><span className="font-medium">{result.clinicalResult.predictedGradeLabel ?? 'No grade prediction'}</span></div>
            {result.clinicalResult.message && <p className="text-sm text-muted-foreground">{result.clinicalResult.message}</p>}
            {result.clinicalResult.gradeScores && <div className="space-y-2 rounded-lg bg-muted/30 p-3"><p className="text-xs text-muted-foreground">Uncalibrated tree vote share by grade (not cancer probabilities)</p>{result.clinicalResult.gradeScores.map(({ grade, voteShare }) => <div key={grade} className="flex justify-between text-xs"><span>Grade {grade}</span><span>{(voteShare * 100).toFixed(1)}%</span></div>)}</div>}
            <p className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">The Module 2 model predicts histologic grade. It does not output cancer probability, and grade is not used as a fusion input.</p>
          </section>
        </div>}
        {result && <section className="space-y-4 rounded-xl border border-border p-4">
          <h3 className="text-sm font-semibold">Image-only Cancer-like / Non-cancer-like scores</h3>
          {(() => {
            const scores = result.imageResult.status === 'success' ? getImageOnlyScores(result.imageResult.probabilities) : null
            return scores ? <div className="space-y-4 rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Re-grouped from Module 1 ultrasound class scores only. These are uncalibrated model scores, not a combined result or clinical cancer probabilities.</p>
              <ProbabilityBar label="Cancer-like (Malignant class)" value={scores.cancerLike} />
              <ProbabilityBar label="Non-cancer-like (Normal + Benign classes)" value={scores.nonCancerLike} />
            </div> : <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-4"><span className="text-sm font-medium">Cancer-like</span><Badge tone="amber">Unavailable</Badge></div>
              <div className="flex items-center justify-between rounded-lg bg-muted/40 p-4"><span className="text-sm font-medium">Non-cancer-like</span><Badge tone="amber">Unavailable</Badge></div>
            </div>
          })()}
          <p className="text-xs leading-relaxed text-muted-foreground">Module 2 grade is shown separately and is not used to increase or decrease these scores. A true image + clinical fusion result requires patient-linked training data with the exact Module 2 inputs and reliable outcomes.</p>
        </section>}
        <p className="text-xs leading-relaxed text-muted-foreground">{result?.disclaimer ?? 'Research output only. These model results are not a medical diagnosis or treatment recommendation.'}</p>
      </div>
    </Panel>
  </div>
}
