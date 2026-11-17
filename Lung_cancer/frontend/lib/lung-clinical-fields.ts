export const LUNG_CLINICAL_FIELDS = [
  { key: 'Age', label: 'Age', min: 1, max: 100, initial: 50 },
  { key: 'Gender', label: 'Gender', min: 1, max: 2, initial: 1 },
  { key: 'Air Pollution', label: 'Air pollution score', min: 1, max: 5, initial: 2 },
  { key: 'Alcohol use', label: 'Alcohol use score', min: 1, max: 5, initial: 2 },
  { key: 'Balanced Diet', label: 'Balanced diet score', min: 1, max: 5, initial: 2 },
  { key: 'Obesity', label: 'Obesity score', min: 1, max: 5, initial: 2 },
  { key: 'Smoking', label: 'Smoking score', min: 1, max: 5, initial: 2 },
  { key: 'Passive Smoker', label: 'Passive smoker score', min: 1, max: 5, initial: 2 },
  { key: 'Fatigue', label: 'Fatigue score', min: 1, max: 5, initial: 2 },
  { key: 'Weight Loss', label: 'Weight loss score', min: 1, max: 5, initial: 2 },
  { key: 'Shortness of Breath', label: 'Shortness of breath score', min: 1, max: 5, initial: 2 },
  { key: 'Wheezing', label: 'Wheezing score', min: 1, max: 5, initial: 2 },
  { key: 'Swallowing Difficulty', label: 'Swallowing difficulty score', min: 1, max: 5, initial: 2 },
  { key: 'Clubbing of Finger Nails', label: 'Nail clubbing score', min: 1, max: 5, initial: 2 },
  { key: 'Frequent Cold', label: 'Frequent cold score', min: 1, max: 5, initial: 2 },
  { key: 'Dry Cough', label: 'Dry cough score', min: 1, max: 5, initial: 2 },
  { key: 'Snoring', label: 'Snoring score', min: 1, max: 5, initial: 2 },
] as const

export type LungClinicalValues = Record<(typeof LUNG_CLINICAL_FIELDS)[number]['key'], number>

export function getInitialLungClinicalValues(): LungClinicalValues {
  return Object.fromEntries(LUNG_CLINICAL_FIELDS.map((field) => [field.key, field.initial])) as LungClinicalValues
}
