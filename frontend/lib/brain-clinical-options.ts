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
