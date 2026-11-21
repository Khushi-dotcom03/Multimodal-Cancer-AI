'use client'

import { useState, type FormEvent } from 'react'
import { Activity, ClipboardCheck, Loader2, Stethoscope } from 'lucide-react'
import { Badge, inputClass, Panel, PanelHeader } from '@/components/common/primitives'

type Answer = '' | 'Yes' | 'No' | 'Not sure'
type SymptomKey = 'lump' | 'nipple' | 'skin' | 'shape'
type AssessmentAnswers = {
  age: number
  sex: string
  symptoms: Record<SymptomKey, Answer>
  familyHistory: Answer
  symptomDuration: string
}
type AssessmentResult = {
  answers: AssessmentAnswers
  assessmentId: string
  status: string
  recommendation: string
  reportedSymptoms: string[]
  unsureSymptoms: string[]
}
type GradeResult = {
  analysisId: string
  status: 'success'
  predictedGrade: number
  predictedGradeLabel: string
  message: string
  gradeScores: { grade: number; voteShare: number }[]
  evaluation: { accuracy: number; macroF1: number; recallByGrade: Record<string, number>; method: string }
  model: {
    name: string
    architecture: string
    dataset: string
    version: string
    trainingStatus: string
    evaluationStatus: string
  }
  disclaimer: string
}

const SYMPTOMS: { key: SymptomKey; label: string }[] = [
  { key: 'lump', label: 'New lump or swelling in breast/chest or armpit' },
  { key: 'nipple', label: 'Unusual nipple changes' },
  { key: 'skin', label: 'Unusual skin changes' },
  { key: 'shape', label: 'Unexpected breast/chest size or shape change' },
]
const ANSWERS: Answer[] = ['Yes', 'No', 'Not sure']
const INITIAL_SYMPTOMS: Record<SymptomKey, Answer> = { lump: '', nipple: '', skin: '', shape: '' }
const INITIAL_GRADE = {
  age: '',
  tumorSize: '',
  er: '',
  pr: '',
  her2: '',
}

function createAssessment(answers: AssessmentAnswers): AssessmentResult {
  const reportedSymptoms = SYMPTOMS.filter(({ key }) => answers.symptoms[key] === 'Yes').map(({ label }) => label)
  const unsureSymptoms = SYMPTOMS.filter(({ key }) => answers.symptoms[key] === 'Not sure').map(({ label }) => label)
  let status: string
  let recommendation: string

  if (reportedSymptoms.length) {
    status = 'One or more new or unusual changes were reported.'
    recommendation = 'Please contact a qualified healthcare professional promptly to discuss these changes and arrange an appropriate medical evaluation. Symptoms can have causes other than cancer.'
  } else if (unsureSymptoms.length) {
    status = 'Some symptom responses were marked Not sure.'
    recommendation = 'If you are uncertain about a change or it concerns you, contact a qualified healthcare professional for advice and assessment.'
  } else {
    status = 'No listed new or unusual symptoms were reported.'
    recommendation = 'Continue routine breast health care. Discuss screening appropriate to your age and personal history with a healthcare professional.'
  }
  if (answers.familyHistory === 'Yes') {
    recommendation += ' You also reported a family history; consider discussing it with a healthcare professional.'
  }

  const date = new Date().toISOString().slice(0, 10).replaceAll('-', '')
  const suffix = crypto.randomUUID().replaceAll('-', '').slice(0, 8).toUpperCase()
  return {
    answers,
    assessmentId: `BHA-${date}-${suffix}`,
    status,
    recommendation,
    reportedSymptoms,
    unsureSymptoms,
  }
}

export function BreastClinicalWorkspace() {
  const [activeTab, setActiveTab] = useState<'assessment' | 'grade'>('assessment')
  const [age, setAge] = useState(18)
  const [sex, setSex] = useState('')
  const [symptoms, setSymptoms] = useState(INITIAL_SYMPTOMS)
  const [familyHistory, setFamilyHistory] = useState<Answer>('')
  const [duration, setDuration] = useState('')
  const [assessment, setAssessment] = useState<AssessmentResult | null>(null)
  const [gradeInput, setGradeInput] = useState(INITIAL_GRADE)
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(null)
  const [gradeError, setGradeError] = useState<string | null>(null)
  const [gradeBusy, setGradeBusy] = useState(false)

  const anySymptomYes = Object.values(symptoms).some((value) => value === 'Yes')
  const symptomFormComplete = Boolean(
    sex && familyHistory && Object.values(symptoms).every(Boolean) && (!anySymptomYes || duration),
  )

  const submitAssessment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!symptomFormComplete) return
    setAssessment(createAssessment({
      age,
      sex,
      symptoms,
      familyHistory,
      symptomDuration: anySymptomYes ? duration : '',
    }))
  }

  const submitGrade = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setGradeBusy(true)
    setGradeError(null)
    setGradeResult(null)
    try {
      const response = await fetch('/api/proxy/breast-clinical-grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          features: {
            'Age at Diagnosis': Number(gradeInput.age),
            'Tumor Size': Number(gradeInput.tumorSize),
            'ER Status': gradeInput.er,
            'PR Status': gradeInput.pr,
            'HER2 Status': gradeInput.her2,
          },
        }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(typeof payload?.detail === 'string' ? payload.detail : `Request failed with status ${response.status}`)
      const result = payload as GradeResult
      setGradeResult(result)
    } catch (error) {
      setGradeError(error instanceof Error ? error.message : 'Clinical grade analysis failed.')
    } finally {
      setGradeBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <nav aria-label="Breast clinical tools" className="-mx-1 overflow-x-auto px-1">
        <div role="tablist" className="flex min-w-max gap-2 border-b border-border">
          <button type="button" role="tab" aria-selected={activeTab === 'assessment'} onClick={() => setActiveTab('assessment')} className={`inline-flex min-h-10 items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${activeTab === 'assessment' ? 'border-wc-turquoise text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
            <Stethoscope className="size-4" aria-hidden /> Breast health assessment
          </button>
          <button type="button" role="tab" aria-selected={activeTab === 'grade'} onClick={() => setActiveTab('grade')} className={`inline-flex min-h-10 items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${activeTab === 'grade' ? 'border-wc-turquoise text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}>
            <Activity className="size-4" aria-hidden /> Histologic grade model
          </button>
        </div>
      </nav>

      {activeTab === 'assessment' ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <Panel className="flex flex-col">
            <PanelHeader title="Breast health assessment" description="Answer each item. Symptom duration appears when any symptom is Yes." icon={Stethoscope} />
            <form onSubmit={submitAssessment} className="flex flex-1 flex-col gap-5 p-5 sm:p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium" htmlFor="breast-assessment-age">Age
                  <input id="breast-assessment-age" className={`${inputClass} mt-1`} type="number" min={0} max={120} value={age} onChange={(event) => setAge(Number(event.target.value))} required />
                </label>
                <label className="text-sm font-medium" htmlFor="breast-assessment-sex">Sex
                  <select id="breast-assessment-sex" className={`${inputClass} mt-1`} value={sex} onChange={(event) => setSex(event.target.value)} required>
                    <option value="">Select an answer</option><option>Female</option><option>Male</option><option>Intersex</option><option>Prefer not to say</option>
                  </select>
                </label>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {SYMPTOMS.map(({ key, label }) => <label key={key} className="text-sm font-medium" htmlFor={`breast-symptom-${key}`}>{label}
                  <select id={`breast-symptom-${key}`} className={`${inputClass} mt-1`} value={symptoms[key]} onChange={(event) => setSymptoms((current) => ({ ...current, [key]: event.target.value as Answer }))} required>
                    <option value="">Select an answer</option>{ANSWERS.map((answer) => <option key={answer}>{answer}</option>)}
                  </select>
                </label>)}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium" htmlFor="breast-family-history">Family history of breast or ovarian cancer
                  <select id="breast-family-history" className={`${inputClass} mt-1`} value={familyHistory} onChange={(event) => setFamilyHistory(event.target.value as Answer)} required>
                    <option value="">Select an answer</option>{ANSWERS.map((answer) => <option key={answer}>{answer}</option>)}
                  </select>
                </label>
                {anySymptomYes && <label className="text-sm font-medium" htmlFor="breast-symptom-duration">How long have symptoms been present?
                  <select id="breast-symptom-duration" className={`${inputClass} mt-1`} value={duration} onChange={(event) => setDuration(event.target.value)} required>
                    <option value="">Select a duration</option><option>Less than 2 weeks</option><option>2–6 weeks</option><option>More than 6 weeks</option><option>Not sure</option>
                  </select>
                </label>}
              </div>
              <button type="submit" disabled={!symptomFormComplete} className="mt-auto inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50">
                <ClipboardCheck className="size-4" aria-hidden /> Create assessment summary
              </button>
              <p className="text-xs leading-relaxed text-muted-foreground">Preliminary symptom summary only. It does not diagnose cancer or estimate cancer probability.</p>
            </form>
          </Panel>

          <Panel className="flex flex-col">
            <PanelHeader title="Assessment summary" description="Your answers are summarized without calculating cancer risk." icon={ClipboardCheck} />
            <div className="flex flex-1 flex-col gap-4 p-5 sm:p-6">
              {!assessment ? <p className="text-sm text-muted-foreground">Complete the questionnaire to display the assessment summary.</p> : <>
                <div className="flex flex-wrap items-center justify-between gap-2"><Badge tone="teal">Summary ready</Badge><span className="text-xs text-muted-foreground">Assessment ID · {assessment.assessmentId}</span></div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs text-muted-foreground">Age</p><p className="mt-1 font-semibold">{assessment.answers.age}</p></div>
                  <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs text-muted-foreground">Sex</p><p className="mt-1 font-semibold">{assessment.answers.sex}</p></div>
                </div>
                <section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold">Assessment status</h3><p className="mt-1 text-sm text-muted-foreground">{assessment.status}</p></section>
                <div className="grid gap-3 sm:grid-cols-2">
                  <section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold">Reported symptoms</h3>{assessment.reportedSymptoms.length ? <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">{assessment.reportedSymptoms.map((item) => <li key={item}>{item}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">No symptom question was answered Yes.</p>}{assessment.answers.symptomDuration && <p className="mt-2 text-xs text-muted-foreground">Duration: {assessment.answers.symptomDuration}</p>}{assessment.unsureSymptoms.length > 0 && <p className="mt-2 text-xs text-muted-foreground">Marked not sure: {assessment.unsureSymptoms.join('; ')}</p>}</section>
                  <section className="rounded-xl border border-border p-4"><h3 className="text-sm font-semibold">Risk factors reported</h3><p className="mt-2 text-sm text-muted-foreground">Family history: {assessment.answers.familyHistory}</p></section>
                </div>
                <section className="rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4"><h3 className="text-sm font-semibold">Recommended medical evaluation</h3><p className="mt-1 text-sm leading-relaxed text-muted-foreground">{assessment.recommendation}</p></section>
              </>}</div>
          </Panel>
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-2">
          <Panel className="flex flex-col">
            <PanelHeader title="Histologic grade prediction" description="Enter the five features used by the existing Module 2 saved pipeline." icon={Activity} />
            <form onSubmit={submitGrade} className="flex flex-1 flex-col gap-5 p-5 sm:p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium" htmlFor="grade-age">Age at Diagnosis
                  <input id="grade-age" className={`${inputClass} mt-1`} type="number" min={0} max={120} step="1" value={gradeInput.age} onChange={(event) => setGradeInput((current) => ({ ...current, age: event.target.value }))} required />
                </label>
                <label className="text-sm font-medium" htmlFor="grade-tumor-size">Tumor Size (mm)
                  <input id="grade-tumor-size" className={`${inputClass} mt-1`} type="number" min={0} step="0.1" value={gradeInput.tumorSize} onChange={(event) => setGradeInput((current) => ({ ...current, tumorSize: event.target.value }))} required />
                  <span className="mt-1 block text-xs font-normal text-muted-foreground">Enter millimetres (for example, 20 mm; convert 2 cm to 20 mm).</span>
                </label>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {([['er', 'ER Status'], ['pr', 'PR Status'], ['her2', 'HER2 Status']] as const).map(([key, label]) => <label key={key} className="text-sm font-medium" htmlFor={`grade-${key}`}>{label}
                  <select id={`grade-${key}`} className={`${inputClass} mt-1`} value={gradeInput[key]} onChange={(event) => setGradeInput((current) => ({ ...current, [key]: event.target.value }))} required>
                    <option value="">Choose</option><option>Positive</option><option>Negative</option>
                  </select>
                </label>)}
              </div>
              <button type="submit" disabled={gradeBusy} className="mt-auto inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-wait disabled:opacity-50">
                {gradeBusy && <Loader2 className="size-4 animate-spin" aria-hidden />}{gradeBusy ? 'Running saved model…' : 'Predict histologic grade'}
              </button>
              {gradeError && <p role="alert" className="rounded-xl border border-red-500/30 bg-red-500/5 p-3 text-sm text-red-700 dark:text-red-300">{gradeError}</p>}
            </form>
          </Panel>

          <Panel className="flex flex-col">
            <PanelHeader title="Model output" description="Prediction from the class-balanced clinical research model." icon={ClipboardCheck} />
            <div className="flex flex-1 flex-col gap-4 p-5 sm:p-6">
              {!gradeResult ? <p className="text-sm text-muted-foreground">Submit the five clinical features to display a grade prediction.</p> : <>
                <div className="rounded-xl border border-border bg-elevated p-4"><p className="text-xs font-semibold uppercase tracking-wider text-wc-teal">Predicted histologic grade</p><p className="mt-2 text-2xl font-bold">{gradeResult.predictedGradeLabel}</p><p className="mt-1 text-sm text-muted-foreground">{gradeResult.message}</p></div>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  <div className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">5-fold CV accuracy</p><p className="mt-1 font-semibold">{(gradeResult.evaluation.accuracy * 100).toFixed(1)}%</p></div>
                  <div className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">CV macro F1</p><p className="mt-1 font-semibold">{gradeResult.evaluation.macroF1.toFixed(3)}</p></div>
                  {[1, 2, 3].map((grade) => <div key={grade} className="rounded-xl border border-border p-3"><p className="text-xs text-muted-foreground">Grade {grade} CV recall</p><p className="mt-1 font-semibold">{((gradeResult.evaluation.recallByGrade[String(grade)] ?? 0) * 100).toFixed(1)}%</p></div>)}
                </div>
                <section className="space-y-3 rounded-xl border border-border p-4">
                  <div><h3 className="text-sm font-semibold">Model vote share by grade</h3><p className="text-xs text-muted-foreground">Uncalibrated tree vote shares; not cancer probabilities or calibrated grade probabilities.</p></div>
                  {gradeResult.gradeScores.map(({ grade, voteShare }) => <div key={grade} className="space-y-1"><div className="flex justify-between text-sm"><span>Grade {grade}</span><span className="tabular-nums">{(voteShare * 100).toFixed(1)}%</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-wc-turquoise" style={{ width: `${Math.max(0, Math.min(1, voteShare)) * 100}%` }} /></div></div>)}
                </section>
                <dl className="grid gap-2 rounded-xl bg-muted/50 p-4 text-sm sm:grid-cols-2">
                  <div><dt className="text-xs text-muted-foreground">Model</dt><dd className="mt-1 font-medium">{gradeResult.model.name}</dd></div>
                  <div><dt className="text-xs text-muted-foreground">Architecture</dt><dd className="mt-1 font-medium">{gradeResult.model.architecture}</dd></div>
                  <div className="sm:col-span-2"><dt className="text-xs text-muted-foreground">Analysis ID</dt><dd className="mt-1 break-all font-mono">{gradeResult.analysisId}</dd></div>
                </dl>
              </>}
              <p className="mt-auto rounded-xl border border-wc-amber/30 bg-wc-amber/8 p-4 text-sm leading-relaxed text-muted-foreground">Grade 1/2/3 research estimate among records similar to the training dataset. The model has modest validation performance, is not a cancer screening tool, does not provide cancer probability, and is not clinically validated.</p>
            </div>
          </Panel>
        </div>
      )}
    </div>
  )
}
