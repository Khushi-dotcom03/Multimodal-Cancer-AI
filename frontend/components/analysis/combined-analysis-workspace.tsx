'use client'

import { useEffect, useState, type ChangeEvent } from 'react'
import { Loader2, Stethoscope } from 'lucide-react'
import { inputClass, Panel, PanelHeader } from '@/components/common/primitives'
import { isApiConfigured } from '@/lib/api-client'
import { padFusionAnalysisService, type PADClinicalDetails } from '@/services/pad-clinical-service'
import type { AnalysisOutcome } from '@/types'
import type { AnalysisPhase } from './analysis-workspace'
import { AnalysisResults } from './analysis-results'
import { ImageUploader } from './image-uploader'

type SymptomAnswer = PADClinicalDetails['itch'] | ''

interface PADForm {
  age: string
  sex: 'female' | 'male' | 'unknown' | ''
  region: string
  itch: SymptomAnswer
  grew: SymptomAnswer
  hurt: SymptomAnswer
  changed: SymptomAnswer
  bleed: SymptomAnswer
  elevation: SymptomAnswer
}

const EMPTY_PAD_FORM: PADForm = {
  age: '',
  sex: '',
  region: '',
  itch: '',
  grew: '',
  hurt: '',
  changed: '',
  bleed: '',
  elevation: '',
}

const REGIONS = ['ABDOMEN', 'ARM', 'BACK', 'CHEST', 'EAR', 'FACE', 'FOOT', 'FOREARM', 'HAND', 'LIP', 'NECK', 'NOSE', 'SCALP', 'THIGH']
const SYMPTOMS: { key: keyof Pick<PADForm, 'itch' | 'grew' | 'hurt' | 'changed' | 'bleed' | 'elevation'>; label: string }[] = [
  { key: 'itch', label: 'Itching' },
  { key: 'grew', label: 'Has it grown?' },
  { key: 'hurt', label: 'Pain or discomfort' },
  { key: 'changed', label: 'Has it changed?' },
  { key: 'bleed', label: 'Bleeding' },
  { key: 'elevation', label: 'Raised / elevated lesion' },
]

export function CombinedAnalysisWorkspace() {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [patient, setPatient] = useState<PADForm>(EMPTY_PAD_FORM)
  const [phase, setPhase] = useState<AnalysisPhase>('idle')
  const [imageOutcome, setImageOutcome] = useState<AnalysisOutcome | null>(null)
  const [imageError, setImageError] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const ageValue = patient.age === '' ? Number.NaN : Number(patient.age)
  const ageValid = Number.isFinite(ageValue) && ageValue >= 0 && ageValue <= 120
  const symptomsValid = SYMPTOMS.every(({ key }) => patient[key] !== '')
  const clinicalValid = ageValid && patient.sex !== '' && Boolean(patient.region) && symptomsValid
  const busy = phase === 'uploading' || phase === 'processing'
  const canAnalyze = Boolean(file) && clinicalValid && isApiConfigured && !busy

  function clearResults() {
    setImageOutcome(null)
    setImageError(null)
    setPhase('idle')
  }

  function handlePatientChange(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.currentTarget
    setPatient((current) => ({ ...current, [name]: value }))
    clearResults()
  }

  async function analyze() {
    if (!file || !clinicalValid || !isApiConfigured || busy) return
    setImageOutcome(null)
    setImageError(null)
    setPhase('uploading')

    const payload: PADClinicalDetails = {
      age: ageValue,
      region: patient.region,
      itch: patient.itch as PADClinicalDetails['itch'],
      grew: patient.grew as PADClinicalDetails['grew'],
      hurt: patient.hurt as PADClinicalDetails['hurt'],
      changed: patient.changed as PADClinicalDetails['changed'],
      bleed: patient.bleed as PADClinicalDetails['bleed'],
      elevation: patient.elevation as PADClinicalDetails['elevation'],
    }

    const toProcessing = setTimeout(() => setPhase('processing'), 500)
    try {
      const result = await padFusionAnalysisService.analyze(file, payload, patient.sex as 'female' | 'male' | 'unknown')
      const outcome: AnalysisOutcome = { kind: 'result', result }
      setImageOutcome(outcome)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'PAD image+clinical fusion failed.'
      setImageError(message)
    }

    clearTimeout(toProcessing)
    setPhase('done')
  }

  function handleFile(next: File | null) {
    setFile(next)
    clearResults()
  }

  const imageResult = imageOutcome?.kind === 'result' ? imageOutcome.result : null

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm leading-relaxed">
        <p className="font-semibold">PAD-UFES-20 image + clinical fusion</p>
        <p className="mt-1 text-muted-foreground">
          The uploaded image and its PAD-UFES-20 clinical details are evaluated together by a patient-disjoint trained fusion model. HAM10000 image-only analysis remains available in Feature 1.
        </p>
      </div>

      <div className="grid items-stretch gap-6 xl:grid-cols-2">
        <ImageUploader file={file} previewUrl={previewUrl} onFileChange={handleFile} disabled={busy} />

        <Panel>
          <PanelHeader
            title="PAD-UFES-20 clinical information"
            description="Enter the clinical details for the same lesion as the uploaded image. Every field is required; Unknown is an explicit option where supported."
            icon={Stethoscope}
          />
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <div>
              <label htmlFor="combined-pad-age" className="mb-1 block text-sm font-medium">Age (years) *</label>
              <input
                id="combined-pad-age"
                name="age"
                type="number"
                min={0}
                max={120}
                step={1}
                required
                value={patient.age}
                onChange={handlePatientChange}
                className={inputClass}
                placeholder="Enter age"
                disabled={busy}
              />
            </div>
            <div>
              <label htmlFor="combined-pad-sex" className="mb-1 block text-sm font-medium">Sex *</label>
              <select id="combined-pad-sex" name="sex" required value={patient.sex} onChange={handlePatientChange} className={inputClass} disabled={busy}>
                <option value="" disabled>Select sex</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>
            <div>
              <label htmlFor="combined-pad-region" className="mb-1 block text-sm font-medium">Lesion region *</label>
              <select id="combined-pad-region" name="region" required value={patient.region} onChange={handlePatientChange} className={inputClass} disabled={busy}>
                <option value="" disabled>Select region</option>
                <option value="UNK">Unknown / not provided</option>
                {REGIONS.map((region) => <option key={region} value={region}>{region.toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}
              </select>
            </div>

            {SYMPTOMS.map(({ key, label }) => (
              <div key={key}>
                <label htmlFor={`combined-pad-${key}`} className="mb-1 block text-sm font-medium">{label} *</label>
                <select id={`combined-pad-${key}`} name={key} required value={patient[key]} onChange={handlePatientChange} className={inputClass} disabled={busy}>
                  <option value="" disabled>Select response</option>
                  <option value="True">Yes</option>
                  <option value="False">No</option>
                  <option value="UNK">Unknown / not provided</option>
                </select>
              </div>
            ))}

            {!ageValid && patient.age !== '' && <p className="text-xs text-red-600 sm:col-span-2">Age must be between 0 and 120 years.</p>}
            <p className="text-xs leading-relaxed text-muted-foreground sm:col-span-2">
              Both input groups must describe the same lesion. This workflow uses the same-dataset PAD-UFES-20 fusion model.
            </p>
            {!isApiConfigured && <p role="alert" className="text-sm text-amber-700 sm:col-span-2">Connect the backend to run analysis.</p>}
            <button
              type="button"
              onClick={analyze}
              disabled={!canAnalyze}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-xl brand-gradient px-5 text-sm font-semibold text-white shadow-lg shadow-wc-teal/20 transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none sm:col-span-2"
            >
              {busy && <Loader2 className="size-4 animate-spin" aria-hidden />}
              {busy ? 'Analyzing fused inputsâ€¦' : 'Analyze Image and Clinical Data'}
            </button>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <div className="flex flex-col gap-3 xl:col-span-2">
          <AnalysisResults
            phase={busy ? phase : imageResult ? 'done' : imageError ? 'error' : 'idle'}
            outcome={imageOutcome}
            error={imageError}
            previewUrl={previewUrl}
            onRetry={analyze}
            title="PAD-UFES-20 combined result"
            description="One joint prediction from the paired PAD image+clinical fusion model."
          />
        </div>

      </div>
    </div>
  )
}


