import { BRAIN_OTHER_SITE } from '@/lib/brain-clinical-options'

export type ObservationState = 'present' | 'absent' | 'unknown'

export interface BrainAssessmentData {
  age: string
  sex: string
  location: string
  symptoms: Record<string, ObservationState>
  symptomLabels: Record<string, string>
  notes: string
}

const valueOrUnknown = (value: string) => value.trim() || 'Unknown / not recorded'

export function buildBrainAssessmentReport(data: BrainAssessmentData) {
  const locationValue = data.location === BRAIN_OTHER_SITE
    ? 'Other / less common location selected; specific site not listed'
    : valueOrUnknown(data.location)
  const profile = [
    `Age: ${valueOrUnknown(data.age)}${data.age.trim() ? ' years' : ''}`,
    `Gender: ${valueOrUnknown(data.sex)}`,
    `Tumour location: ${locationValue}`,
  ]

  const symptoms = Object.entries(data.symptomLabels).map(([key, label]) => {
    const state = data.symptoms[key] ?? 'unknown'
    const display = state === 'present' ? 'Present' : state === 'absent' ? 'Absent' : 'Unknown / not recorded'
    return `${label}: ${display}`
  })

  const missing: string[] = []
  if (!data.age.trim()) missing.push('Age')
  if (!data.sex.trim()) missing.push('Gender')
  if (!data.location.trim()) missing.push('Tumour location')
  else if (data.location === BRAIN_OTHER_SITE) missing.push('Specific tumour location (other / less common selected)')
  for (const [key, label] of Object.entries(data.symptomLabels)) {
    if ((data.symptoms[key] ?? 'unknown') === 'unknown') missing.push(`${label} status`)
  }

  const present = Object.entries(data.symptomLabels)
    .filter(([key]) => data.symptoms[key] === 'present')
    .map(([, label]) => label)
  const absent = Object.entries(data.symptomLabels)
    .filter(([key]) => data.symptoms[key] === 'absent')
    .map(([, label]) => label)
  const summaryParts = [
    `Patient profile recorded as age ${valueOrUnknown(data.age)}${data.age.trim() ? ' years' : ''}, gender ${valueOrUnknown(data.sex)}, and tumour location ${locationValue}.`,
    present.length ? `Symptoms marked present: ${present.join(', ')}.` : 'No symptom was marked as present in this assessment.',
    absent.length ? `Symptoms marked absent: ${absent.join(', ')}.` : '',
    data.notes.trim() ? 'Additional clinical notes are included as entered.' : '',
  ].filter(Boolean)

  return {
    sections: {
      profile,
      symptoms,
      missing: missing.length ? missing : ['No profile or symptom-status fields are missing.'],
      summary: summaryParts,
    },
    text: [
      'Brain Clinical Assessment & Reporting',
      '', '1. Patient profile', ...profile,
      '', '2. Presenting symptoms', ...symptoms,
      '', '3. Missing or unavailable information', ...missing.map((item) => `- ${item}`),
      '', '4. Clinical information summary', ...summaryParts,
      ...(data.notes.trim() ? ['', 'Additional clinical notes', data.notes.trim()] : []),
    ].join('\n'),
  }
}
