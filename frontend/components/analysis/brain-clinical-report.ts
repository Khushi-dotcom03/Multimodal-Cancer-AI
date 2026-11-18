import { BRAIN_OTHER_SITE } from '@/lib/brain-clinical-options'

export type ObservationState = 'present' | 'absent' | 'unknown'

export interface BrainAssessmentData {
  age: string
  sex: string
  location: string
  symptoms: Record<string, ObservationState>
  symptomLabels: Record<string, string>
  radiology: Record<string, string>
  radiologyLabels: Record<string, string>
  dimensions: { length: string; width: string; height: string; unit: 'mm' | 'cm' }
  provenance: string
  notes: string
}

const valueOrUnknown = (value: string) => value.trim() || 'Unknown / not recorded'

export function buildBrainAssessmentReport(data: BrainAssessmentData) {
  const locationValue = data.location === BRAIN_OTHER_SITE
    ? 'Other / less common location selected; specific site not listed'
    : valueOrUnknown(data.location)
  const profile = [
    `Age: ${valueOrUnknown(data.age)}${data.age.trim() ? ' years' : ''}`,
    `Sex: ${valueOrUnknown(data.sex)}`,
    `Tumour location: ${locationValue}`,
  ]

  const symptoms = Object.entries(data.symptomLabels).map(([key, label]) => {
    const state = data.symptoms[key] ?? 'unknown'
    const display = state === 'present' ? 'Present' : state === 'absent' ? 'Absent' : 'Unknown / not recorded'
    return `${label}: ${display}`
  })

  const radiology = Object.entries(data.radiologyLabels).map(([key, label]) => `${label}: ${valueOrUnknown(data.radiology[key] ?? '')}`)
  const enteredDimensions = [data.dimensions.length, data.dimensions.width, data.dimensions.height]
  const anyDimension = enteredDimensions.some((value) => value.trim())
  const allDimensions = enteredDimensions.every((value) => value.trim())
  const dimensionSummary = anyDimension ? `${enteredDimensions.map((value) => value.trim() || 'not recorded').join(' × ')} ${data.dimensions.unit}${allDimensions ? '' : ' (partial)'}` : 'Unknown / not recorded'
  radiology.push(`Lesion dimensions: ${dimensionSummary}`)
  radiology.push(`Information source: ${valueOrUnknown(data.provenance)}`)
  if (data.notes.trim()) radiology.push(`Additional notes (as entered): ${data.notes.trim()}`)

  const missing: string[] = []
  if (!data.age.trim()) missing.push('Age')
  if (!data.sex.trim() || data.sex === 'Unknown / not recorded') missing.push('Sex')
  if (!data.location.trim()) missing.push('Tumour location')
  else if (data.location === BRAIN_OTHER_SITE) missing.push('Specific tumour location (other / less common selected)')
  for (const [key, label] of Object.entries(data.symptomLabels)) {
    if ((data.symptoms[key] ?? 'unknown') === 'unknown') missing.push(`${label} status`)
  }
  for (const [key, label] of Object.entries(data.radiologyLabels)) {
    if (!data.radiology[key] || data.radiology[key] === 'Unknown / not recorded') missing.push(label)
  }
  if (!allDimensions) missing.push('Complete lesion dimensions')
  if (!data.provenance || data.provenance === 'Unknown / not recorded') missing.push('Radiology information source')
  if (!data.notes.trim()) missing.push('Additional notes (optional; none entered)')

  const present = Object.entries(data.symptomLabels)
    .filter(([key]) => data.symptoms[key] === 'present')
    .map(([, label]) => label)
  const absent = Object.entries(data.symptomLabels)
    .filter(([key]) => data.symptoms[key] === 'absent')
    .map(([, label]) => label)
  const knownRadiology = Object.entries(data.radiologyLabels)
    .filter(([key]) => data.radiology[key] && data.radiology[key] !== 'Unknown / not recorded')
    .map(([key, label]) => `${label}: ${data.radiology[key]}`)
  const summaryParts = [
    `Patient profile recorded as age ${valueOrUnknown(data.age)}${data.age.trim() ? ' years' : ''}, sex ${valueOrUnknown(data.sex)}, and tumour location ${locationValue}.`,
    present.length ? `Symptoms marked present: ${present.join(', ')}.` : 'No symptom was marked as present in this assessment.',
    absent.length ? `Symptoms marked absent: ${absent.join(', ')}.` : '',
    knownRadiology.length ? `Radiology fields entered (${valueOrUnknown(data.provenance)}): ${knownRadiology.join('; ')}.` : 'No radiology observation was recorded.',
    anyDimension ? `Lesion dimensions entered: ${dimensionSummary}.` : '',
    data.notes.trim() ? 'Additional notes are included verbatim in the report.' : '',
  ].filter(Boolean)

  return {
    sections: { profile, symptoms, radiology, missing: missing.length ? missing : ['No required profile or assessment fields are missing.'], summary: summaryParts },
    text: [
      'Brain Clinical Assessment & Reporting',
      '', '1. Patient profile', ...profile,
      '', '2. Presenting symptoms', ...symptoms,
      '', '3. Radiology findings', ...radiology,
      '', '4. Missing or unavailable information', ...missing.map((item) => `- ${item}`),
      '', '5. Clinical information summary', ...summaryParts,
    ].join('\n'),
  }
}
