
'use client'

import { useState, type FormEvent } from 'react'
import { Activity, Loader2, Stethoscope } from 'lucide-react'
import { Badge, EmptyState, inputClass, Panel, PanelHeader } from '@/components/common/primitives'
import { isApiConfigured } from '@/lib/api-client'
import {
  padClinicalAnalysisService,
  type PADClinicalDetails,
  type PADClinicalRequest,
  type PADClinicalResult,
} from '@/services/pad-clinical-service'

const INITIAL_PATIENT: PADClinicalRequest = {
  age: 45,
  sex: '',
  region: 'UNK',
  itch: 'UNK',
  grew: 'UNK',
  hurt: 'UNK',
  changed: 'UNK',
  bleed: 'UNK',
  elevation: 'UNK',
}

const SYMPTOMS: {
  key: keyof Pick<
    PADClinicalDetails,
    'itch' | 'grew' | 'hurt' | 'changed' | 'bleed' | 'elevation'
  >
  label: string
}[] = [
  { key: 'itch', label: 'Itching' },
  { key: 'grew', label: 'Has it grown?' },
  { key: 'hurt', label: 'Pain or discomfort' },
  { key: 'changed', label: 'Has it changed?' },
  { key: 'bleed', label: 'Bleeding' },
  { key: 'elevation', label: 'Raised / elevated lesion' },
]

const REGIONS = [
  'ABDOMEN', 'ARM', 'BACK', 'CHEST', 'EAR', 'FACE', 'FOOT',
  'FOREARM', 'HAND', 'LIP', 'NECK', 'NOSE', 'SCALP', 'THIGH',
]

const CLASS_NAMES: Record<string, string> = {
  ACK: 'Actinic keratosis',
  BCC: 'Basal cell carcinoma',
  MEL: 'Melanoma',
  NEV: 'Nevus',
  SCC: 'Squamous cell carcinoma',
  SEK: 'Seborrheic keratosis',
}

export function PADClinicalAnalysisWorkspace() {
  const [patient, setPatient] = useState<PADClinicalRequest>(INITIAL_PATIENT)
  const [result, setResult] = useState<PADClinicalResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const invalidAge =
    !Number.isFinite(patient.age) ||
    patient.age < 0 ||
    patient.age > 120


  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (invalidAge || !isApiConfigured) return

    setBusy(true)
    setError(null)
    setResult(null)

    try {
      setResult(await padClinicalAnalysisService.analyze(patient))
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'PAD clinical analysis failed.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-5">
      <Panel className="xl:col-span-2">
        <PanelHeader
          title="Clinical information"
          description="Enter the clinical features supported by the configured research model."
          icon={Stethoscope}
        />

        <form onSubmit={submit} className="flex flex-col gap-4 p-5 sm:p-6">
          <div>
            <label htmlFor="pad-age" className="mb-1 block text-sm font-medium">
              Age (years)
            </label>
            <input
              id="pad-age"
              type="number"
              min={0}
              max={120}
              required
              value={patient.age}
              onChange={(e) =>
                setPatient({ ...patient, age: Number(e.target.value) })
              }
              className={inputClass}
            />
            {invalidAge && (
              <p className="mt-1 text-xs text-red-600">
                Enter an age between 0 and 120.
              </p>
            )}
          </div>

          <div>
            <label htmlFor="pad-sex" className="mb-1 block text-sm font-medium">
              Sex *
            </label>
            <select
              id="pad-sex"
              required
              value={patient.sex}
              onChange={(e) =>
                setPatient({
                  ...patient,
                  sex: e.target.value as PADClinicalRequest['sex'],
                })
              }
              className={inputClass}
            >
              <option value="" disabled>Select sex</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="unknown">Not provided</option>
            </select>
          </div>

          <div>
            <label htmlFor="pad-region" className="mb-1 block text-sm font-medium">
              Lesion region
            </label>
            <select
              id="pad-region"
              required
              value={patient.region}
              onChange={(e) =>
                setPatient({ ...patient, region: e.target.value })
              }
              className={inputClass}
            >
              <option value="UNK">Unknown / Not provided</option>
              {REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())}
                </option>
              ))}
            </select>
          </div>

          {SYMPTOMS.map(({ key, label }) => (
            <div key={key}>
              <label
                htmlFor={`pad-${key}`}
                className="mb-1 block text-sm font-medium"
              >
                {label}
              </label>
              <select
                id={`pad-${key}`}
                value={patient[key]}
                onChange={(e) =>
                  setPatient({ ...patient, [key]: e.target.value })
                }
                className={inputClass}
              >
                <option value="UNK">Unknown / Not provided</option>
                <option value="True">Yes</option>
                <option value="False">No</option>
              </select>
            </div>
          ))}


          <p className="text-xs leading-relaxed text-muted-foreground">
            Unknown values are kept distinct from No. This research result is
            not a medical diagnosis. Sex is recorded in the report but is not
            an input to the existing PAD clinical model.
          </p>

          <button
            type="submit"
            disabled={
              !isApiConfigured ||
              busy ||
              invalidAge ||
              !patient.region.trim() ||
              !patient.sex
            }
            className="inline-flex h-11 items-center justify-center gap-2 rounded-xl brand-gradient px-5 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy && <Loader2 className="size-4 animate-spin" />}
            {busy ? 'Analyzing...' : 'Run Clinical Analysis'}
          </button>

          {!isApiConfigured && (
            <p role="alert" className="text-sm text-amber-700">
              Set NEXT_PUBLIC_API_URL to connect the backend.
            </p>
          )}

          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
        </form>
      </Panel>

      <Panel className="xl:col-span-3">
        <PanelHeader
          title="Clinical analysis results"
          description="Output from the configured clinical research model."
          icon={Activity}
          action={result && <Badge tone="emerald">Model output</Badge>}
        />

        <div className="p-5 sm:p-6">
          {result ? (
            <div className="flex flex-col gap-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <Tile
                  label="Predicted category"
                  value={`${result.prediction} (${result.classification})`}
                />
                <Tile
                  label="Model confidence"
                  value={`${(result.confidence * 100).toFixed(2)}%`}
                />
                <Tile label="Analysis ID" value={result.analysisId} />
              </div>


              {result.sexUsage && (
                <p className="text-xs text-muted-foreground">
                  {result.sexUsage}
                </p>
              )}

              <div className="rounded-xl border border-border p-4">
                <h3 className="text-sm font-semibold">Class scores</h3>

                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {Object.entries(result.probabilities).map(
                    ([code, probability]) => (
                      <div key={code}>
                        <div className="mb-1 flex justify-between gap-2 text-xs">
                          <span>
                            {CLASS_NAMES[code] ?? code} ({code})
                          </span>
                          <span>{(probability * 100).toFixed(2)}%</span>
                        </div>

                        <div className="h-2 rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-wc-turquoise"
                            style={{
                              width: `${Math.max(
                                0,
                                Math.min(100, probability * 100),
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    ),
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-border p-4">
                <h3 className="text-sm font-semibold">Model information</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {result.model.name}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {result.model.architecture}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Dataset: {result.dataset}
                </p>
              </div>

              <a
                href={`/reports?analysisId=${encodeURIComponent(result.analysisId)}`}
                className="inline-flex h-10 items-center justify-center self-start rounded-xl border border-border px-4 text-sm font-semibold hover:bg-muted"
              >
                View detailed report
              </a>

              <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
                <p className="text-sm font-semibold">Research disclaimer</p>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  {result.disclaimer}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  Model confidence is not a calibrated real-world disease
                  probability. This result must not be used for self-diagnosis
                  or treatment decisions.
                </p>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Activity}
              title="No clinical analysis yet"
              description="Enter the supported clinical information and run the model. An image is not required for this module."
            />
          )}
        </div>
      </Panel>
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-border bg-elevated p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 break-all text-sm font-semibold">{value}</p>
    </div>
  )
}
