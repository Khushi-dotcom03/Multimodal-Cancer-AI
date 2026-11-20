// Common, cleaned tumour locations from IPD-Brain's SITE field.
// The long tail remains unrecorded unless a listed canonical option is usable.
export const BRAIN_LOCATION_GROUPS = [
  { label: 'Frontal', values: ['frontal', 'left frontal', 'right frontal', 'bilateral frontal', 'bifrontal', 'left inferior frontal', 'left medial frontal', 'right frontal pole', 'right superior frontal'] },
  { label: 'Temporal', values: ['temporal', 'left temporal', 'right temporal', 'left posterior temporal', 'posterior temporal', 'medial temporal', 'mesial temporal', 'left temporal hippocampus', 'left temporal and sylvian'] },
  { label: 'Parietal', values: ['parietal', 'left parietal', 'right parietal', 'posterior parietal', 'right inferior parietal lobule'] },
  { label: 'Occipital', values: ['occipital', 'left occipital', 'right occipital'] },
  { label: 'Combined regions', values: ['fronto temporal', 'left fronto temporal', 'right frontal temporal', 'fronto parietal', 'left fronto parietal', 'right fronto parietal', 'temporo parietal', 'left temporo parietal', 'right temporo parietal', 'parieto occipital', 'left parieto occipital', 'right parieto occipital', 'temporo occipital', 'frontotemporoparietal'] },
  { label: 'Other recorded structures', values: ['insular', 'left insular', 'right insular', 'thalamus', 'left thalamus', 'corpus callosum', 'lateral ventricle', 'right lateral ventricle corpus callosum', 'cerebellar', 'left cerebellum', 'motor cortex', 'left premotor', 'right premotor', 'supracellar', 'falx cerebri', 'multicentric'] },
] as const

export const BRAIN_UNKNOWN = 'Unknown / not recorded'
export const BRAIN_OTHER_SITE = '__other__'

export type BrainClinicalScreeningStatus = 'insufficient' | 'suspicion' | 'no_indicators'

export function getBrainClinicalScreeningStatus(
  symptoms: Record<string, 'present' | 'absent' | 'unknown'>,
  touched: Record<string, boolean>,
  symptomKeys: readonly string[],
): BrainClinicalScreeningStatus {
  if (symptomKeys.length === 0 || symptomKeys.some((key) => !touched[key])) return 'insufficient'

  const presentCount = symptomKeys.filter((key) => symptoms[key] === 'present').length
  if (presentCount >= 2) return 'suspicion'
  if (presentCount === 0) return 'no_indicators'
  return 'insufficient'
}

export function hasRequiredBrainSubtypeInputs(age: string, gender: string, location: string) {
  const numericAge = Number(age)
  return age.trim() !== ''
    && Number.isInteger(numericAge)
    && numericAge >= 5
    && numericAge <= 78
    && (gender === 'Female' || gender === 'Male')
    && location.trim() !== ''
    && location !== BRAIN_OTHER_SITE
}
