'use client'

/* eslint-disable @next/next/no-img-element -- upload previews and model data URLs */
import { useEffect, useState } from 'react'
import { Activity, BrainCircuit, Flame, Layers3, Loader2, ShieldAlert } from 'lucide-react'
import { Panel, PanelHeader, inputClass } from '@/components/common/primitives'
import { BRAIN_LOCATION_GROUPS, BRAIN_OTHER_SITE, BRAIN_UNKNOWN } from '@/lib/brain-clinical-options'
import { analyzeBrainMultimodal, type BrainMultimodalResult } from '@/services/brain-multimodal-service'
import { BrainMRIUploader } from './brain-mri-uploader'

const IMAGE_CLASSES = ['Glioma', 'Meningioma', 'No Tumor', 'Pituitary Tumor']
const CLINICAL_LABELS: Record<string, string> = {
  GLIOBLASTOMA: 'Glioblastoma', ASTROCYTOMA: 'Astrocytoma', OLIGODENDROGLIOMA: 'Oligodendroglioma',
}
const selectClass = `${inputClass} bg-background`

export function BrainMultimodalWorkspace() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [age, setAge] = useState('')
  const [sex, setSex] = useState<'M' | 'F' | ''>('')
  const [site, setSite] = useState('')
  const [result, setResult] = useState<BrainMultimodalResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!file) { setPreview(null); return }
    const url = URL.createObjectURL(file)
    setPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const analyze = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const numericAge = Number(age)
    if (!file) { setError('Choose a brain MRI image before starting the combined analysis.'); return }
    if (!age.trim() || !Number.isInteger(numericAge) || numericAge < 5 || numericAge > 78) {
      setError('Age must be an integer from 5 to 78, matching the clinical model training range.')
      return
    }
    if (!sex) { setError('Choose the sex value recorded for this case.'); return }

    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const response = await analyzeBrainMultimodal({
        file, age: numericAge, sex,
        site: site && site !== BRAIN_OTHER_SITE ? site : undefined,
      })
      setResult(response)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Brain multimodal analysis failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  return <div className="flex flex-col gap-6">
    <div className="rounded-2xl border border-wc-cyan/20 bg-wc-cyan/5 p-4 text-sm leading-6">
      <div className="flex items-start gap-3"><Layers3 className="mt-0.5 size-5 shrink-0 text-wc-cyan" /><p><strong>One image-plus-clinical workflow.</strong> The original MRI classifier and saved Age + Sex + Site model both run on submission. This project has no brain-specific jointly trained fusion checkpoint or paired training set, so their real outputs are shown together as separate research results rather than a fabricated combined probability.</p></div>
    </div>

    <form onSubmit={analyze} className="grid gap-6 xl:grid-cols-5">
      <div className="xl:col-span-3">
        <BrainMRIUploader file={file} previewUrl={preview} disabled={busy} onFileChange={(next) => { setFile(next); setResult(null); setError(null) }} />
      </div>
      <Panel className="flex flex-col">
        <PanelHeader title="Clinical information" description="These are the saved clinical model fields. Symptoms and radiology remain available in the separate assessment/report workflow." icon={Activity} />
        <div className="flex flex-1 flex-col gap-5 p-5 sm:p-6">
          <div>
            <label htmlFor="brain-multimodal-age" className="mb-1.5 block text-sm font-medium">Age</label>
            <input id="brain-multimodal-age" type="number" min={5} max={78} step={1} required value={age} onChange={(e) => setAge(e.target.value)} className={inputClass} placeholder="Age in years" />
            <p className="mt-1.5 text-xs text-muted-foreground">Accepted range: 5–78 years.</p>
          </div>
          <div>
            <label htmlFor="brain-multimodal-sex" className="mb-1.5 block text-sm font-medium">Sex recorded for this case</label>
            <select id="brain-multimodal-sex" required value={sex} onChange={(e) => setSex(e.target.value as 'M' | 'F' | '')} className={selectClass}>
              <option value="" disabled>Select recorded value</option><option value="F">Female</option><option value="M">Male</option>
            </select>
          </div>
          <div>
            <label htmlFor="brain-multimodal-site" className="mb-1.5 block text-sm font-medium">Tumour location</label>
            <select id="brain-multimodal-site" value={site} onChange={(e) => setSite(e.target.value)} className={selectClass}>
              <option value="">{BRAIN_UNKNOWN}</option>
              {BRAIN_LOCATION_GROUPS.map((group) => <optgroup key={group.label} label={group.label}>{group.values.map((value) => <option key={value} value={value}>{value.replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}</optgroup>)}
              <option value={BRAIN_OTHER_SITE}>Other / less common (specific site not listed)</option>
            </select>
          </div>
          <p className="mt-auto text-xs leading-5 text-muted-foreground">The clinical output estimates subtype among IPD-Brain glioma cases. It does not determine whether the image contains a tumour.</p>
          <button type="submit" disabled={!file || busy} className="inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? <Loader2 className="size-4 animate-spin" /> : <BrainCircuit className="size-4" />}{busy ? 'Analyzing image and clinical data…' : 'Analyze Image + Clinical Data'}
          </button>
        </div>
      </Panel>
    </form>

    {error && <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/5 p-4 text-sm text-red-700 dark:text-red-300"><strong>Analysis unavailable.</strong> {error}</div>}
    {busy && <div aria-live="polite" className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-card p-8 text-sm font-medium"><Loader2 className="size-5 animate-spin text-wc-cyan" />Running the two saved brain research models…</div>}
    {result && <CombinedResult result={result} preview={preview} age={age} sex={sex} site={site} />}
  </div>
}

function CombinedResult({ result, preview, age, sex, site }: { result: BrainMultimodalResult; preview: string | null; age: string; sex: string; site: string }) {
  const clinicalPredicted = result.clinicalResult.predictedSubtype
  const imageScores = result.imageResult.classScores
  const clinicalScores = result.clinicalResult.classScores

  return <Panel aria-live="polite">
    <PanelHeader title="Brain multimodal research result" description="Both modalities were processed for this assessment. The image and clinical outputs are independent model results." icon={Layers3} />
    <div className="flex flex-col gap-5 p-5 sm:p-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-wc-violet/25 bg-wc-violet/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-wc-violet">MRI image model · top class</p>
          <h3 className="mt-1 text-xl font-bold">{result.imageResult.predictedClass}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{result.imageResult.architecture} · uncalibrated softmax scores</p>
        </div>
        <div className="rounded-xl border border-wc-cyan/25 bg-wc-cyan/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-wc-teal dark:text-wc-cyan">Clinical model · top subtype score</p>
          <h3 className="mt-1 text-xl font-bold">{result.clinicalResult.predictedSubtypeLabel}</h3>
          <p className="mt-1 text-xs text-muted-foreground">Glioma subtype cohort model · uncalibrated scores</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ScoreCard title="MRI class scores" scores={imageScores} labels={{}} predicted={result.imageResult.predictedClass} />
        <ScoreCard title="Clinical glioma subtype scores" scores={clinicalScores} labels={CLINICAL_LABELS} predicted={clinicalPredicted} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-border p-4">
          <h3 className="flex items-center gap-2 text-sm font-semibold"><Flame className="size-4 text-wc-pink" /> MRI visualization</h3>
          <div className="mt-3 grid grid-cols-3 gap-2">{[
            { label: 'Original', src: preview },
            { label: 'Grad-CAM', src: result.imageResult.gradcam.heatmap },
            { label: 'Overlay', src: result.imageResult.gradcam.overlay },
          ].map(({ label, src }) => <figure key={label} className="min-w-0"><div className="flex aspect-square items-center justify-center overflow-hidden rounded-lg bg-muted">{src ? <img src={src} alt={`${label} brain MRI`} className="size-full object-contain" /> : <span className="px-2 text-center text-xs text-muted-foreground">{label === 'Original' ? 'Image unavailable' : 'Grad-CAM unavailable'}</span>}</div><figcaption className="mt-1.5 text-center text-xs text-muted-foreground">{label}</figcaption></figure>)}</div>
          {!result.imageResult.gradcam.available && <p className="mt-3 text-xs text-amber-700 dark:text-amber-300">Grad-CAM is unavailable for this image; the MRI class output is still shown.</p>}
        </div>
        <div className="rounded-xl border border-border p-4">
          <h3 className="text-sm font-semibold">Clinical inputs</h3>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm"><Summary label="Age" value={`${age} years`} /><Summary label="Sex" value={sex === 'F' ? 'Female' : 'Male'} /><Summary label="Tumour location" value={site === BRAIN_OTHER_SITE ? 'Other / not listed' : site || 'Not provided'} /><Summary label="Analysis ID" value={result.analysisId} /></dl>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">Clinical model features: {result.clinicalResult.model.features.join(', ')}.</p>
        </div>
      </div>

      <p className="rounded-xl border border-wc-cyan/25 bg-wc-cyan/5 p-4 text-sm leading-6"><strong>Cross-modal summary:</strong> the MRI model's top category is {result.imageResult.predictedClass}; the separate clinical model's highest glioma subtype score is {result.clinicalResult.predictedSubtypeLabel}. These outputs use different class sets and are not combined into a single probability.</p>
      <p className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6"><ShieldAlert className="mr-2 inline size-4" />Experimental research outputs; not clinically validated and not a diagnosis. The clinical model represents glioma cases in IPD-Brain and does not verify the MRI result. {resultScopeText(result)}</p>
      <div className="grid gap-3 sm:grid-cols-2"><p className="rounded-lg border border-border p-3 text-xs leading-5">{result.imageResult.disclaimer}</p><p className="rounded-lg border border-border p-3 text-xs leading-5">{result.clinicalResult.disclaimer}</p></div>
    </div>
  </Panel>
}

function resultScopeText(result: BrainMultimodalResult) {
  return result.resultScope.note
}

function ScoreCard({ title, scores, labels, predicted }: { title: string; scores: Record<string, number>; labels: Record<string, string>; predicted: string }) {
  return <div className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold">{title}</h3><p className="mt-1 text-xs text-muted-foreground">Uncalibrated model scores, not calibrated probabilities.</p><div className="mt-4 space-y-3">{Object.entries(scores).map(([name, value]) => <div key={name}><div className="mb-1 flex justify-between gap-3 text-sm"><span className={name === predicted ? 'font-semibold' : 'text-muted-foreground'}>{labels[name] ?? name}{name === predicted ? ' · highest' : ''}</span><span className="font-mono">{(value * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-full rounded-full ${name === predicted ? 'bg-wc-violet' : 'bg-wc-cyan/60'}`} style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div></div>)}</div></div>
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium">{value}</dd></div>
}
