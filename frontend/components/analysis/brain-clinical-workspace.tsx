'use client'

import { useState } from 'react'
import { Activity, BrainCircuit, Clipboard, FileText, Loader2, Printer, RotateCcw } from 'lucide-react'
import { Panel, PanelHeader, inputClass } from '@/components/common/primitives'
import { analyzeBrainClinical, type BrainClinicalResult } from '@/services/brain-clinical-service'
import { BRAIN_LOCATION_GROUPS as LOCATION_GROUPS, BRAIN_OTHER_SITE, BRAIN_UNKNOWN as UNKNOWN, getBrainClinicalScreeningStatus, hasRequiredBrainSubtypeInputs } from '@/lib/brain-clinical-options'
import { buildBrainAssessmentReport, type BrainAssessmentData, type ObservationState } from './brain-clinical-report'
import { saveBrainChatContext } from '@/lib/brain-chat-context'

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

const selectClass = `${inputClass} bg-background`

export function BrainClinicalWorkspace() {
  const [age, setAge] = useState('')
  const [sex, setSex] = useState('')
  const [location, setLocation] = useState('')
  const [symptoms, setSymptoms] = useState<Record<string, ObservationState>>(() => Object.fromEntries(SYMPTOMS.map(({ key }) => [key, 'unknown'])))
  const [symptomsTouched, setSymptomsTouched] = useState<Record<string, boolean>>({})
  const [notes, setNotes] = useState('')
  const [report, setReport] = useState<ReturnType<typeof buildBrainAssessmentReport> | null>(null)
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'error'>('idle')
  const [result, setResult] = useState<BrainClinicalResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [subtypeInsufficient, setSubtypeInsufficient] = useState(false)
  const [busy, setBusy] = useState(false)
  const screeningStatus = getBrainClinicalScreeningStatus(symptoms, symptomsTouched, SYMPTOMS.map(({ key }) => key))

  const clearSubtypeResult = () => {
    setResult(null)
    setError(null)
    setSubtypeInsufficient(false)
  }

  const updateSymptom = (key: string, value: ObservationState) => {
    setSymptoms((previous) => ({ ...previous, [key]: value }))
    setSymptomsTouched((previous) => ({ ...previous, [key]: true }))
    clearSubtypeResult()
  }

  const assessmentData = (): BrainAssessmentData => ({
    age, sex, location, symptoms,
    symptomLabels: Object.fromEntries(SYMPTOMS.map(({ key, label }) => [key, label])),
    notes,
  })

  const generateReport = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const assessment = assessmentData()
    const generatedReport = buildBrainAssessmentReport(assessment)
    setReport(generatedReport)
    saveBrainChatContext('brain_clinical', {
      userEnteredAssessment: {
        patientProfile: { age: assessment.age || 'Unknown / not recorded', sex: assessment.sex || 'Unknown / not recorded', tumorLocation: assessment.location || 'Unknown / not recorded' },
        symptoms: Object.fromEntries(Object.entries(assessment.symptoms).map(([key, state]) => [assessment.symptomLabels[key] ?? key, state])),
      },
      reportSummary: generatedReport.sections.summary,
    })
    setCopyState('idle')
    setResult(null)
    setError(null)
    setSubtypeInsufficient(false)
    if (screeningStatus !== 'suspicion') return
    const numericAge = Number(age)
    if (!hasRequiredBrainSubtypeInputs(age, sex, location)) {
      setSubtypeInsufficient(true)
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      // This call deliberately sends only the original model features.
      const response = await analyzeBrainClinical({ age: numericAge, sex: sex === 'Female' ? 'F' : 'M', site: location })
      setResult(response)
      saveBrainChatContext('brain_clinical', {
        actualApplicationResult: {
          predictedSubtype: response.predictedSubtypeLabel,
          classScores: response.classScores,
          scoreType: response.scoreType,
          modelName: response.model.name,
          architecture: response.model.architecture,
          target: response.model.target,
        },
        userProvidedValues: { age: numericAge, sex, site: location || 'Not provided' },
      })
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
          <p className="text-xs leading-5 text-muted-foreground sm:col-span-2">Age (5–78), Gender, and a listed tumour location are required only for subtype analysis. The rule-based screening uses symptom selections only.</p>
          <div>
            <label htmlFor="brain-assessment-age" className="mb-1.5 block text-sm font-medium">Age</label>
            <input id="brain-assessment-age" type="number" inputMode="numeric" step="any" value={age} onChange={(e) => { setAge(e.target.value); clearSubtypeResult() }} className={inputClass} placeholder="Age in years (5–78)" />
          </div>
          <div>
            <label htmlFor="brain-assessment-gender" className="mb-1.5 block text-sm font-medium">Gender</label>
            <select id="brain-assessment-gender" value={sex} onChange={(e) => { setSex(e.target.value); clearSubtypeResult() }} className={selectClass}>
              <option value="" disabled>Select gender</option><option value="Female">Female</option><option value="Male">Male</option>
            </select>
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="brain-assessment-location" className="mb-1.5 block text-sm font-medium">Tumour location</label>
            <select id="brain-assessment-location" value={location} onChange={(e) => { setLocation(e.target.value); clearSubtypeResult() }} className={selectClass}>
              <option value="">{UNKNOWN}</option>
              {LOCATION_GROUPS.map((group) => <optgroup key={group.label} label={group.label}>{group.values.map((value) => <option key={value} value={value}>{value.replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}</optgroup>)}
              <option value={BRAIN_OTHER_SITE}>Other / less common (specific site not listed)</option>
            </select>
            <p className="mt-1.5 text-xs text-muted-foreground">Choose a listed location to run the subtype model. “Other / less common” is not sufficient for this model.</p>
          </div>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="2. Presenting symptoms" description="Select a status for every item to complete this rule-based demo screening. These are not model inputs." icon={FileText} />
        <div className="divide-y divide-border px-5 sm:px-6">
          {SYMPTOMS.map(({ key, label, mentions }) => <div key={key} className="grid gap-2 py-4 sm:grid-cols-[minmax(0,1fr)_minmax(260px,0.9fr)] sm:items-center">
            <div><p className="text-sm font-medium">{label}</p><p className="mt-0.5 text-xs text-muted-foreground">Mentioned in {mentions} of 327 reviewed records; chart completeness varies.</p></div>
            <div role="group" aria-label={`${label} status`} className="grid grid-cols-3 gap-2">
              {(['present', 'absent', 'unknown'] as const).map((value) => <label key={value} className={`flex min-h-10 cursor-pointer items-center justify-center rounded-lg border px-2 text-center text-xs font-medium transition-colors ${symptoms[key] === value ? 'border-primary bg-primary/10 text-primary' : 'border-border hover:bg-muted'}`}>
                <input className="sr-only" type="radio" name={`symptom-${key}`} value={value} checked={symptoms[key] === value} onChange={() => updateSymptom(key, value)} onClick={() => setSymptomsTouched((previous) => ({ ...previous, [key]: true }))} />
                {value === 'present' ? 'Present' : value === 'absent' ? 'Absent' : 'Unknown'}
              </label>)}
            </div>
          </div>)}
          <div className="py-4">
            <label htmlFor="brain-assessment-notes" className="mb-1.5 block text-sm font-medium">Additional clinical notes <span className="text-xs font-normal text-muted-foreground">(optional)</span></label>
            <textarea id="brain-assessment-notes" maxLength={2000} rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} className={`${inputClass} min-h-24 resize-y`} placeholder="Add relevant information as recorded. Avoid identifiers." />
          </div>
        </div>
      </Panel>

      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <p className="max-w-2xl text-xs leading-5 text-muted-foreground">The preliminary screening updates from your symptom selections. Analyze runs the subtype model only if suspicion is flagged and its required inputs are available.</p>
        <button type="submit" disabled={busy} className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50">{busy ? <Loader2 className="size-4 animate-spin" /> : <FileText className="size-4" />}{busy ? 'Analyzing…' : 'Analyze'}</button>
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
        <ReportSection number="3" title="Missing or unavailable information" items={report.sections.missing} muted />
        <div className="rounded-xl border border-wc-cyan/25 bg-wc-cyan/5 p-4"><h3 className="text-sm font-semibold">4. Clinical information summary</h3><div className="mt-2 space-y-2 text-sm leading-6">{report.sections.summary.map((line, index) => <p key={index}>{line}</p>)}</div></div>
      </div>
    </Panel>}

    <Panel aria-live="polite">
      <PanelHeader title="1. Preliminary screening" description="Automatic symptom-count rule for demonstration only; it does not detect or rule out cancer." icon={BrainCircuit} />
      <div className="flex flex-col gap-4 p-5 sm:p-6">
        <p className="text-xs font-medium text-muted-foreground">Rule-based demo screening — not clinically validated</p>
        <div className={`rounded-xl border p-4 text-sm leading-6 ${screeningStatus === 'suspicion' ? 'border-wc-amber/40 bg-wc-amber/10' : 'border-border bg-muted/30'}`}>
          <strong>{screeningStatus === 'suspicion' ? 'SUSPICION FLAG — FURTHER EVALUATION' : screeningStatus === 'no_indicators' ? 'NO SIGNIFICANT INDICATORS SELECTED' : 'INSUFFICIENT DATA'}</strong>
          {screeningStatus === 'insufficient' && <p className="mt-1">Select a status for every symptom. The demo requires at least two symptoms marked Present to raise a suspicion flag.</p>}
          {screeningStatus === 'no_indicators' && <p className="mt-1">No symptoms were marked Present in the completed symptom section. This does not rule out cancer.</p>}
          {screeningStatus === 'suspicion' && <p className="mt-1">At least two symptoms are marked Present. This rule is not a validated cancer screening method.</p>}
        </div>
        {screeningStatus === 'suspicion' && <section className="flex flex-col gap-4 border-t border-border pt-4">
          <div><h3 className="text-base font-semibold">2. Glioma subtype classification</h3><p className="mt-1 text-xs text-muted-foreground">Existing IPD-Brain three-class model; experimental and not clinically validated.</p></div>
          {subtypeInsufficient && <div role="status" className="rounded-xl border border-border bg-muted/30 p-4 text-sm"><strong>Insufficient data for subtype classification.</strong><p className="mt-1">Provide a valid age (5–78), gender, and a listed tumour location, then select Analyze.</p></div>}
          {error && <div role="status" className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6"><strong>Classification not included.</strong> {error}</div>}
          {busy && <div aria-live="polite" className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 text-sm"><Loader2 className="size-4 animate-spin text-wc-cyan" />Running the existing Age + Sex + Site research model…</div>}
          {result && <ResearchResult result={result} />}
        </section>}
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
    <div className="rounded-xl border border-wc-violet/30 bg-wc-violet/5 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-wc-violet">Predicted glioma subtype</p><h3 className="mt-1 text-2xl font-semibold">{result.predictedSubtypeLabel}</h3><p className="mt-1 text-xs text-muted-foreground">Existing IPD-Brain model output · uncalibrated class scores.</p></div>
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Subtype scores</h4><p className="mt-1 text-xs text-muted-foreground">Scores are not calibrated probabilities.</p><div className="mt-4 space-y-3">{Object.entries(result.classScores).map(([label, value]) => <div key={label}><div className="mb-1 flex justify-between gap-3 text-sm"><span>{SUBTYPE_LABELS[label] ?? label}{label === result.predictedSubtype ? ' · highest' : ''}</span><span className="font-mono">{(value * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-violet/70" style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div></div>)}</div></div>
      <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Research input summary</h4><dl className="mt-3 grid grid-cols-2 gap-3 text-sm"><Summary label="Age" value={`${result.inputSummary.age} years`} /><Summary label="Gender" value={result.inputSummary.sex} /><Summary label="Site" value={result.inputSummary.site} /><Summary label="Analysis ID" value={result.analysisId} /></dl><p className="mt-4 text-xs leading-5 text-muted-foreground">Input features: {result.model.features.join(', ')}.</p></div>
    </div>
    <div className="rounded-xl border border-border p-4"><h4 className="text-sm font-semibold">Model evaluation context</h4><p className="mt-1 text-xs leading-5 text-muted-foreground">One held-out patient-level test split; this is research performance context, not patient-specific confidence or clinical validation. Validation macro F1: {(result.model.validationMacroF1 * 100).toFixed(1)}%.</p><div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">{[['Accuracy',result.model.testMetrics.accuracy],['Balanced accuracy',result.model.testMetrics.balanced_accuracy],['Macro precision',result.model.testMetrics.macro_precision],['Macro recall',result.model.testMetrics.macro_recall],['Macro F1',result.model.testMetrics.macro_f1],['Majority baseline F1',result.model.majorityBaseline.macro_f1]].map(([label, metric]) => <div key={String(label)} className="rounded-lg bg-muted/60 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-lg font-semibold">{(Number(metric) * 100).toFixed(1)}%</p></div>)}</div><div className="mt-4 overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-muted-foreground"><tr><th className="py-2 pr-3 font-medium">Subtype</th><th className="py-2 pr-3 font-medium">Precision</th><th className="py-2 pr-3 font-medium">Recall</th><th className="py-2 font-medium">Test cases</th></tr></thead><tbody>{Object.entries(result.model.testMetrics.per_class).map(([label, values]) => <tr key={label} className="border-t border-border"><th className="py-2 pr-3 font-medium">{SUBTYPE_LABELS[label] ?? label}</th><td className="py-2 pr-3">{(values.precision * 100).toFixed(1)}%</td><td className="py-2 pr-3">{(values.recall * 100).toFixed(1)}%</td><td className="py-2">{values.support}</td></tr>)}</tbody></table></div></div>
    <p className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-6">{result.disclaimer} This model classifies glioma subtypes and is not designed to screen for cancer vs. non-cancer.</p>
  </div>
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0"><dt className="text-xs text-muted-foreground">{label}</dt><dd className="mt-1 break-words font-medium">{value}</dd></div>
}
