'use client'

import { useState } from 'react'
import { Activity, BrainCircuit, Clipboard, FileText, Loader2, Printer, RotateCcw } from 'lucide-react'
import { Panel, PanelHeader, inputClass } from '@/components/common/primitives'
import { analyzeBrainClinical, type BrainClinicalResult } from '@/services/brain-clinical-service'
import { BRAIN_LOCATION_GROUPS as LOCATION_GROUPS, BRAIN_OTHER_SITE, BRAIN_UNKNOWN as UNKNOWN } from '@/lib/brain-clinical-options'
import { buildBrainAssessmentReport, type BrainAssessmentData, type ObservationState } from './brain-clinical-report'

const SUBTYPE_LABELS: Record<string, string> = {
  GLIOBLASTOMA: 'Glioblastoma', ASTROCYTOMA: 'Astrocytoma', OLIGODENDROGLIOMA: 'Oligodendroglioma',
}

const SYMPTOMS = [
  { key: 'headache', label: 'Headache', mentions: 143 },
  { key: 'vomiting', label: 'Vomiting', mentions: 40 },
  { key: 'seizures', label: 'Seizures', mentions: 80 },
  { key: 'limb_weakness', label: 'Limb weakness', mentions: 52 },
  { key: 'dizziness', label: 'Dizziness / giddiness', mentions: 18 },
  { key: 'loss_consciousness', label: 'Loss of consciousness', mentions: 4 },
  { key: 'speech', label: 'Speech disturbance', mentions: 23 },
  { key: 'visual', label: 'Visual disturbance', mentions: 12 },
  { key: 'memory', label: 'Memory disturbance', mentions: 13 },
  { key: 'behavior', label: 'Personality / behavioural changes', mentions: 5 },
] as const

const RADIOLOGY = [
  { key: 't1', label: 'T1 signal', options: ['Hypointense', 'Isointense', 'Hyperintense', 'Heterogeneous'] },
  { key: 't2_flair', label: 'T2 / FLAIR signal', options: ['Hypointense', 'Isointense', 'Hyperintense', 'Heterogeneous'] },
  { key: 'enhancement', label: 'Contrast enhancement', options: ['Present', 'Absent', 'Heterogeneous', 'Homogeneous', 'Ring-like'] },
] as const

const FINDINGS = [
  { key: 'edema', label: 'Perilesional edema' },
  { key: 'cystic', label: 'Cystic component' },
  { key: 'mass_effect', label: 'Mass effect' },
  { key: 'midline_shift', label: 'Midline shift' },
] as const

const selectClass = `${inputClass} bg-background`

export function BrainClinicalWorkspace() {
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('')
  const [location, setLocation] = useState('')
  const [symptoms, setSymptoms] = useState<Record<string, ObservationState>>(() => Object.fromEntries(SYMPTOMS.map(({ key }) => [key, 'unknown'])))
  const [radiology, setRadiology] = useState<Record<string, string>>(() => Object.fromEntries([...RADIOLOGY, ...FINDINGS].map(({ key }) => [key, UNKNOWN])))
  const [dimensions, setDimensions] = useState({ length: '', width: '', height: '', unit: 'cm' as 'mm' | 'cm' })
  const [provenance, setProvenance] = useState('')
  const [notes, setNotes] = useState('')
  const [report, setReport] = useState<ReturnType<typeof buildBrainAssessmentReport> | null>(null)
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle')
  const [result, setResult] = useState<BrainClinicalResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const assessmentData = (): BrainAssessmentData => ({
    age, sex, location, symptoms,
    symptomLabels: Object.fromEntries(SYMPTOMS.map(({ key, label }) => [key, label])),
    radiology, radiologyLabels: Object.fromEntries([...RADIOLOGY, ...FINDINGS].map(({ key, label }) => [key, label])),
    dimensions, provenance, notes,
  })

  const generateReport = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setReport(buildBrainAssessmentReport(assessmentData()))
    setCopyState('idle')
    setResult(null)
    setError(null)
    const numericAge = Number(age)
    if (!age.trim() || !Number.isInteger(numericAge) || numericAge < 5 || numericAge > 78) {
      setError('The report is ready. To include the experimental subtype classification, enter an integer age from 5 to 78, matching the model training cohort.')
      return
    }
    if (sex !== 'Female' && sex !== 'Male') {
      setError('The report is ready. To include the experimental subtype classification, select Female or Male, the values represented in the model training data.')
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      // This call deliberately sends only the original model features.
      const response = await analyzeBrainClinical({ age: numericAge, sex: sex === 'Female' ? 'F' : 'M', site: location && location !== BRAIN_OTHER_SITE ? location : undefined })
      setResult(response)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The research model is unavailable. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const copyReport = async () => {
    if (!report) return
    try {
      await navigator.clipboard.writeText(report.text)
      setCopyState('copied')
    } catch {
      setCopyState('error')
    }
  }

  return <div className="brain-clinical-page flex flex-col gap-6">
    <div className="rounded-2xl border border-wc-cyan/20 bg-wc-cyan/5 p-4 text-sm leading-6">
      <div className="flex items-start gap-3"><Activity className="mt-0.5 size-5 shrink-0 text-wc-cyan" /><p><strong>Clinical information workflow.</strong> Record observations and create a structured report from the information entered. This workflow does not produce a diagnosis or treatment recommendation.</p></div>
    </div>

    <form onSubmit={generateReport} className="flex flex-col gap-6">
      <Panel>
        <PanelHeader title="1. Patient information" description="Enter only information available for this assessment. Do not enter patient identifiers." icon={Activity} />
        <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
          <div>
            <label htmlFor="brain-assessment-age" className="mb-1.5 block text-sm font-medium">Age <span className="text-xs font-normal text-muted-foreground">(optional)</span></label>
            <input id="brain-assessment-age" type="number" inputMode="numeric" min={0} max={120} step={1} value={age} onChange={(e) => setAge(e.target.value)} className={inputClass} placeholder="Age in years" />
          </div>
          <div>
            <label htmlFor="brain-assessment-sex" className="mb-1.5 block text-sm font-medium">Sex <span className="text-xs font-normal text-muted-foreground">(optional)</span></label>
            <select id="brain-assessment-sex" value={sex} onChange={(e) => setSex(e.target.value)} className={selectClass}>
              <option value="">{UNKNOWN}</option><option value="Female">Female</option><option value="Male">Male</option><option value="Other">Other</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="brain-assessment-location" className="mb-1.5 block text-sm font-medium">Tumour location</label>
            <select id="brain-assessment-location" value={location} onChange={(e) => setLocation(e.target.value)} className={selectClass}>
              <option value="">{UNKNOWN}</option>
              {LOCATION_GROUPS.map((group) => <optgroup key={group.label} label={group.label}>{group.values.map((value) => <option key={value} value={value}>{value.replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}</optgroup>)}
              <option value={BRAIN_OTHER_SITE}>Other / less common (specific site not listed)</option>
            </select>
            <p className="mt-1.5 text-xs text-muted-foreground">Options reflect common cleaned locations in IPD-Brain. Unknown or less common sites can remain unrecorded.</p>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="2. Presenting symptoms" description="Choose Present, Absent, or Unknown / not recorded for each item. These are supported to varying degrees by mentions in the IPD-Brain records; they are not model inputs." icon={FileText} />
        <div className="divide-y divide-border px-5 sm:px-6">
          {SYMPTOMS.map(({ key, label, mentions }) => <div key={key} className="grid gap-2 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(260px,0.9fr)] sm:items-center">
            <div><p className="text-sm font-medium">{label}</p><p className="mt-0.5 text-xs text-muted-foreground">Mentioned in {mentions} of 327 reviewed records; chart completeness varies.</p></div>
            <div role="group" aria-label={`${label} status`} className="grid grid-cols-3 gap-2">
              {(['present', 'absent', 'unknown'] as const).map((value) => <label key={value} className={`flex min-h-10 cursor-pointer items-center justify-center rounded-lg border px-2 text-center text-xs font-medium transition-colors ${symptoms[key] === value ? 'border-primary bg-primary/10 text-primary' : 'border-border hover:bg-muted'}`}>
                <input className="sr-only" type="radio" name={`symptom-${key}`} value={value} checked={symptoms[key] === value} onChange={() => setSymptoms((previous) => ({ ...previous, [key]: value }))} />
                {value === 'present' ? 'Present' : value === 'absent' ? 'Absent' : 'Unknown'}
              </label>)}
            </div>
          </div>)}
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="3. Radiology findings" description="Enter findings only when available. Select the source to distinguish patient or caregiver observations from a verified radiology report." icon={FileText} />
        <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
          {[...RADIOLOGY, ...FINDINGS].map(({ key, label, options }: { key: string; label: string; options?: readonly string[] }) => <div key={key}>
            <label htmlFor={`brain-radiology-${key}`} className="mb-1.5 block text-sm font-medium">{label}</label>
            <select id={`brain-radiology-${key}`} value={radiology[key]} onChange={(e) => setRadiology((previous) => ({ ...previous, [key]: e.target.value }))} className={selectClass}>
              <option value={UNKNOWN}>{UNKNOWN}</option>
              {options ? options.map((option) => <option key={option} value={option}>{option}</option>) : <><option value="Present">Present</option><option value="Absent">Absent</option></>}
            </select>
          </div>)}
          <div className="sm:col-span-2">
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">Lesion dimensions <span className="text-xs font-normal text-muted-foreground">(optional)</span></legend>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-[1fr_1fr_1fr_110px]">
                {(['length', 'width', 'height'] as const).map((dimension) => <div key={dimension}>
                  <label htmlFor={`brain-dimension-${dimension}`} className="sr-only">{dimension}</label>
                  <input id={`brain-dimension-${dimension}`} type="number" inputMode="decimal" min={0.1} max={1000} step="any" value={dimensions[dimension]} onChange={(e) => setDimensions((previous) => ({ ...previous, [dimension]: e.target.value }))} className={inputClass} placeholder={`${dimension[0].toUpperCase()}${dimension.slice(1)}`} />
                </div>)}
                <div><label htmlFor="brain-dimension-unit" className="sr-only">Dimension unit</label><select id="brain-dimension-unit" value={dimensions.unit} onChange={(e) => setDimensions((previous) => ({ ...previous, unit: e.target.value as 'mm' | 'cm' }))} className={selectClass}><option value="mm">mm</option><option value="cm">cm</option></select></div>
              </div>
            </fieldset>
          </div>
          <div>
            <label htmlFor="brain-radiology-source" className="mb-1.5 block text-sm font-medium">Radiology information source</label>
            <select id="brain-radiology-source" value={provenance} onChange={(e) => setProvenance(e.target.value)} className={selectClass}>
              <option value="">{UNKNOWN}</option><option value="Patient / caregiver reported">Patient / caregiver reported</option><option value="Verified radiology report">Verified radiology report</option>
            </select>
            <p className="mt-1.5 text-xs text-muted-foreground">Select “Verified radiology report” only when checked against the report.</p>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="brain-assessment-notes" className="mb-1.5 block text-sm font-medium">Additional notes <span className="text-xs font-normal text-muted-foreground">(optional)</span></label>
            <textarea id="brain-assessment-notes" maxLength={2000} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="Add relevant information as recorded. Avoid identifiers." />
          </div>
        </div>
      </Panel>

      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <p className="max-w-2xl text-xs leading-5 text-muted-foreground">Unknown and unavailable findings remain explicitly unknown. Report generation is local; when the required profile fields are available, this action also requests the separate subtype classification.</p>
        <button type="submit" disabled={busy} className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}{busy ? 'Generating report and classification…' : 'Generate report'}</button>
      </div>
    </form>

    {report && <Panel className="brain-assessment-print" aria-live="polite">
      <PanelHeader title="Clinical assessment report" description="A deterministic summary of the information entered above." icon={FileText} />
      <div className="report-actions flex flex-wrap gap-2 border-b border-border px-5 py-3 sm:px-6">
        <button type="button" onClick={copyReport} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm font-medium hover:bg-muted"><Clipboard className="size-4" />{copyState === 'copied' ? 'Copied' : 'Copy report'}</button>
        <button type="button" onClick={() => window.print()} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm font-medium hover:bg-muted"><Printer className="size-4" />Print report</button>
        <button type="button" onClick={() => setReport(null)} className="inline-flex h-9 items-center gap-2 rounded-lg border border-border px-3 text-sm font-medium hover:bg-muted"><RotateCcw className="size-4" />Close report</button>
        {copyState === 'error' && <span role="status" className="self-center text-xs text-muted-foreground">Clipboard access unavailable in this browser.</span>}
      </div>
      <div className="grid gap-4 p-5 sm:p-6">
        <ReportSection number="1" title="Patient profile" items={report.sections.profile} />
        <ReportSection number="2" title="Presenting symptoms" items={report.sections.symptoms} />
        <ReportSection number="3" title="Radiology findings" items={report.sections.radiology} />
        <ReportSection number="4" title="Missing or unavailable information" items={report.sections.missing} muted />
        <div className="rounded-xl border border-wc-cyan/25 bg-wc-cyan/5 p-4"><h3 className="text-sm font-semibold">5. Clinical information summary</h3><div className="mt-2 space-y-2 text-sm leading-6">{report.sections.summary.map((line, index) => <p key={index}>{line}</p>)}</div></div>
      </div>
    </Panel>}

    <Panel>
        <PanelHeader title={result ? 'Clinical research result' : 'Glioma subtype classification'} description={result ? 'Experimental glioma subtype output from the saved IPD-Brain model.' : 'The report action also requests a separate subtype result when the required profile fields are available.'} icon={BrainCircuit} />
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        <div className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6"><strong>Experimental; not clinically validated.</strong> This model classifies among the three glioma subtypes represented in IPD-Brain. It is not a diagnosis and does not detect whether a tumour is present. Class scores are uncalibrated. The symptom and radiology sections remain part of the assessment record; current experiment results did not support using their extracted values as classifier inputs.</div>
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <p className="max-w-2xl text-xs leading-5 text-muted-foreground">The classification follows the complete assessment workflow. The separate saved subtype model evaluates Age, Sex, and Tumour location; the accompanying report preserves the remaining submitted information.</p>
        </div>
        {error && <div role="status" className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6"><strong>Classification not included.</strong> {error}</div>}
        {busy && <div aria-live="polite" className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 text-sm"><Loader2 className="size-4 animate-spin text-wc-cyan" />The report is ready; running the saved Age + Sex + Site research model…</div>}
        {result && <ResearchResult result={result} />}
      </div>
    </Panel>
    <style jsx global>{`
      @media print {
        body * { visibility: hidden !important; }
        .brain-assessment-print, .brain-assessment-print * { visibility: visible !important; }
        .brain-assessment-print { position: absolute; inset: 0; width: 100%; border: 0 !important; box-shadow: none !important; }
        .brain-assessment-print .report-actions { display: none !important; }
      }
    `}</style>
  </div>
}

function ReportSection({ number, title, items, muted = false }: { number: string; title: string; items: string[]; muted?: boolean }) {
  return <section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold">{number}. {title}</h3><ul className={`mt-2 grid gap-1 text-sm leading-6 ${muted ? 'text-muted-foreground' : ''}`}>{items.map((item) => <li key={item}>{item}</li>)}</ul></section>
}

function ResearchResult({ result }: { result: BrainClinicalResult }) {
  return <div aria-live="polite" className="grid gap-5 border-t border-border pt-5">
    <div className="flex flex-wrap items-start justify-between gap-3 rounded-xl bg-wc-violet/8 p-4">
      <div><p className="text-xs font-semibold uppercase tracking-wider text-wc-violet">Predicted subtype</p><h3 className="mt-1 text-xl font-bold">{result.predictedSubtypeLabel}</h3><p className="mt-1 text-xs text-muted-foreground">Highest scoring class · uncalibrated model scores · not a diagnosis</p></div>
      <span className="rounded-full bg-wc-violet/10 px-3 py-1 text-xs font-semibold text-wc-violet">{result.model.architecture}</span>
    </div>
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Subtype scores</h4><p className="mt-1 text-xs text-muted-foreground">Scores are not calibrated probabilities.</p><div className="mt-4 space-y-3">{Object.entries(result.classScores).map(([label, value]) => <div key={label}><div className="mb-1 flex justify-between gap-3 text-sm"><span>{SUBTYPE_LABELS[label] ?? label}{label === result.predictedSubtype ? ' · highest' : ''}</span><span className="font-mono">{(value * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-violet/70" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div></div>)}</div></div>
      <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Research input summary</h4><dl className="mt-3 grid grid-cols-2 gap-3 text-sm"><Summary label="Age" value={`${result.inputSummary.age} years`} /><Summary label="Sex" value={result.inputSummary.sex} /><Summary label="Site" value={result.inputSummary.site} /><Summary label="Analysis ID" value={result.analysisId} /></dl><p className="mt-4 text-xs leading-5 text-muted-foreground">Input features: {result.model.features.join(', ')}.</p></div>
    </div>
    <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Model evaluation context</h4><p className="mt-1 text-xs leading-5 text-muted-foreground">One held-out patient-level test split; this is research performance context, not patient-specific confidence or clinical validation. Validation macro F1: {(result.model.validationMacroF1 * 100).toFixed(1)}%.</p><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">{[['Accuracy',result.model.testMetrics.accuracy],['Balanced accuracy',result.model.testMetrics.balanced_accuracy],['Macro precision',result.model.testMetrics.macro_precision],['Macro recall',result.model.testMetrics.macro_recall],['Macro F1',result.model.testMetrics.macro_f1],['Majority baseline F1',result.model.majorityBaseline.macro_f1]].map(([label, metric]) => <div key={String(label)} className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-lg font-semibold">{(Number(metric) * 100).toFixed(1)}%</p></div>)}</div><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-muted-foreground"><tr><th className="py-2 pr-3 font-medium">Subtype</th><th className="py-2 pr-3 font-medium">Precision</th><th className="py-2 pr-3 font-medium">Recall</th><th className="py-2 font-medium">Test cases</th></tr></thead><tbody>{Object.entries(result.model.testMetrics.per_class).map(([label, values]) => <tr key={label} className="border-t border-border"><th className="py-2 pr-3 font-medium">{SUBTYPE_LABELS[label] ?? label}</th><td className="py-2 pr-3">{(values.precision * 100).toFixed(1)}%</td><td className="py-2 pr-3">{(values.recall * 100).toFixed(1)}%</td><td className="py-2">{values.support}</td></tr>)}</tbody></table></div></div>
    <p className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6">{result.disclaimer}</p>
  </div>
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium">{value}</dd></div>
}
