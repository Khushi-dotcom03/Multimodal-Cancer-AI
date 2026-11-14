import assert from 'node:assert/strict'
import test from 'node:test'
import { buildBrainAssessmentReport } from '../components/analysis/brain-clinical-report.ts'

const symptomLabels = {
  headache: 'Headache', vomiting: 'Vomiting', seizures: 'Seizures', limb_weakness: 'Limb weakness',
  dizziness: 'Dizziness / giddiness', loss_consciousness: 'Loss of consciousness', speech: 'Speech disturbance',
  visual: 'Visual disturbance', memory: 'Memory disturbance', behavior: 'Personality / behavioural changes',
}
const radiologyLabels = {
  t1: 'T1 signal', t2_flair: 'T2 / FLAIR signal', enhancement: 'Contrast enhancement',
  edema: 'Perilesional edema', cystic: 'Cystic component', mass_effect: 'Mass effect', midline_shift: 'Midline shift',
}
const blankData = () => ({
  age: '', sex: '', location: '',
  symptoms: Object.fromEntries(Object.keys(symptomLabels).map((key) => [key, 'unknown'])), symptomLabels,
  radiology: Object.fromEntries(Object.keys(radiologyLabels).map((key) => [key, 'Unknown / not recorded'])), radiologyLabels,
  dimensions: { length: '', width: '', height: '', unit: 'cm' }, provenance: '', notes: '',
})

test('incomplete information stays unknown and report does not invent findings', () => {
  const report = buildBrainAssessmentReport(blankData())
  assert.match(report.text, /Age: Unknown \/ not recorded/)
  assert.match(report.text, /Headache: Unknown \/ not recorded/)
  assert.match(report.text, /T1 signal: Unknown \/ not recorded/)
  assert.match(report.text, /Lesion dimensions: Unknown \/ not recorded/)
  assert.match(report.text, /No radiology observation was recorded\./)
  assert.doesNotMatch(report.text, /Glioblastoma|Astrocytoma|Oligodendroglioma/i)
  assert.doesNotMatch(report.text, /This report restates entered information|not a diagnosis or treatment recommendation/i)
  assert.ok(report.sections.missing.includes('Age'))
  assert.ok(report.sections.missing.includes('Headache status'))
})

test('all entered profile, symptom states, radiology values, dimensions, source and notes are reflected', () => {
  const data = blankData()
  data.age = '42'
  data.sex = 'Female'
  data.location = 'left frontal'
  data.symptoms = Object.fromEntries(Object.keys(symptomLabels).map((key, index) => [key, index % 3 === 0 ? 'present' : index % 3 === 1 ? 'absent' : 'unknown']))
  data.radiology = { t1: 'Hypointense', t2_flair: 'Hyperintense', enhancement: 'Ring-like', edema: 'Present', cystic: 'Absent', mass_effect: 'Present', midline_shift: 'Unknown / not recorded' }
  data.dimensions = { length: '3.2', width: '2.1', height: '', unit: 'cm' }
  data.provenance = 'Verified radiology report'
  data.notes = 'Additional observation entered by the user.'

  const report = buildBrainAssessmentReport(data)
  for (const expected of [
    'Age: 42 years', 'Sex: Female', 'Tumour location: left frontal',
    'Headache: Present', 'Vomiting: Absent', 'Seizures: Unknown / not recorded',
    'T1 signal: Hypointense', 'T2 / FLAIR signal: Hyperintense', 'Contrast enhancement: Ring-like',
    'Perilesional edema: Present', 'Cystic component: Absent', 'Mass effect: Present',
    'Midline shift: Unknown / not recorded', '3.2 × 2.1 × not recorded cm (partial)',
    'Information source: Verified radiology report', 'Additional notes (as entered): Additional observation entered by the user.',
  ]) assert.ok(report.text.includes(expected), `Expected report to include: ${expected}`)
  for (const label of Object.values(symptomLabels)) assert.ok(report.text.includes(`${label}:`), `Missing symptom field: ${label}`)
  for (const label of Object.values(radiologyLabels)) assert.ok(report.text.includes(`${label}:`), `Missing radiology field: ${label}`)
  assert.doesNotMatch(report.text, /This report restates entered information|not a diagnosis or treatment recommendation/i)
  assert.doesNotMatch(report.text, /The findings indicate|consistent with|likely/i)
})

test('other location is documented without fabricating a specific site', () => {
  const data = blankData()
  data.location = '__other__'
  const report = buildBrainAssessmentReport(data)
  assert.match(report.text, /Tumour location: Other \/ less common location selected; specific site not listed/)
  assert.ok(report.sections.missing.includes('Specific tumour location (other / less common selected)'))
  assert.doesNotMatch(report.text, /frontal|temporal|parietal|occipital/i)
})
