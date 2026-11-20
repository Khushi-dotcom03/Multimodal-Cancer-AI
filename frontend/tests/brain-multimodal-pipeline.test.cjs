const assert = require('node:assert/strict')
const fs = require('node:fs')
const Module = require('node:module')
const path = require('node:path')
const test = require('node:test')
const ts = require('typescript')

const pipelinePath = path.join(__dirname, '..', 'services', 'brain-multimodal-pipeline.ts')
const source = fs.readFileSync(pipelinePath, 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText
const pipelineModule = new Module(pipelinePath, module)
pipelineModule.filename = pipelinePath
pipelineModule.paths = Module._nodeModulePaths(path.dirname(pipelinePath))
pipelineModule._compile(compiled, pipelinePath)
const { getMRIScreeningDisplay, normalizeBrainClinicalStageResult, runBrainMultimodalPipeline } = pipelineModule.exports

const imageResult = {
  analysisId: 'mri-test', moduleId: 'brain-tumour', prediction: 'No Tumor', confidence: 0.91,
  classification: 'No Tumor', model: {}, createdAt: 'test', isDemo: false,
  classScores: { 'No Tumor': 0.91, glioma: 0.03, meningioma: 0.03, 'pituitary tumor': 0.03 },
}
const tumorImageResult = {
  ...imageResult,
  prediction: 'Glioma', classification: 'Glioma', confidence: 0.82,
  classScores: { 'No Tumor': 0.1, Glioma: 0.82, Meningioma: 0.04, 'Pituitary Tumor': 0.04 },
}
const idhResult = {
  task: 'research prediction of IDH status', predicted_class: 'wild type',
  class_scores: { 'wild type': 0.7, mutated: 0.3 }, score_interpretation: 'uncalibrated',
  model: 'test model', n_slices_used: 1, checkpoint: 'test.pt',
}

function dependencies(overrides = {}) {
  return {
    analyzeImage: async () => ({ kind: 'result', result: tumorImageResult }),
    analyzeClinical: async () => ({
      analysisId: 'clinical-test', predictedSubtype: 'ASTROCYTOMA',
      predictedSubtypeLabel: 'Astrocytoma', classScores: { ASTROCYTOMA: 0.8, GLIOBLASTOMA: 0.2 },
      scoreType: 'uncalibrated model scores',
    }),
    analyzeIdh: async () => idhResult,
    ...overrides,
  }
}

function input({ files = [{ name: 'slice.png' }], clinical = { age: 52, sex: 'F' } } = {}) {
  return { files, clinical, idh: { ageAtImaging: 52, sexAtBirth: 'F' } }
}

test('direct standalone clinical response maps to the multimodal result shape', async () => {
  const result = await runBrainMultimodalPipeline(input(), dependencies())
  assert.equal(result.clinical.status, 'success')
  assert.equal(result.clinical.result.predictedSubtypeLabel, 'Astrocytoma')
  assert.deepEqual(result.clinical.result.classScores, { ASTROCYTOMA: 0.8, GLIOBLASTOMA: 0.2 })
})

test('No Tumor MRI skips clinical and IDH without calling either inference function', async () => {
  let clinicalCalled = false
  let idhCalled = false
  const result = await runBrainMultimodalPipeline(input(), dependencies({
    analyzeImage: async () => ({ kind: 'result', result: imageResult }),
    analyzeClinical: async () => { clinicalCalled = true; return dependencies().analyzeClinical() },
    analyzeIdh: async () => { idhCalled = true; return idhResult },
  }))
  assert.equal(result.mri.status, 'success')
  assert.equal(result.mri.result.tumorSlices, 0)
  assert.equal(result.mri.result.prediction, 'No Tumor')
  assert.deepEqual(result.mri.result.classScores, imageResult.classScores)
  assert.equal(result.clinical.status, 'skipped')
  assert.equal(result.idh.status, 'skipped')
  assert.equal(result.clinical.message, 'Skipped because MRI screening predicted No Tumor.')
  assert.equal(result.idh.message, 'Skipped because MRI screening predicted No Tumor.')
  assert.equal(clinicalCalled, false)
  assert.equal(idhCalled, false)
})

test('No_Tumor class mapping is normalized and gates both later stages', async () => {
  let clinicalCalled = false
  let idhCalled = false
  const result = await runBrainMultimodalPipeline(input(), dependencies({
    analyzeImage: async () => ({ kind: 'result', result: { ...imageResult, prediction: 'no_tumor', classification: 'no_tumor' } }),
    analyzeClinical: async () => { clinicalCalled = true; return dependencies().analyzeClinical() },
    analyzeIdh: async () => { idhCalled = true; return idhResult },
  }))
  assert.equal(result.clinical.status, 'skipped')
  assert.equal(result.idh.status, 'skipped')
  assert.equal(clinicalCalled, false)
  assert.equal(idhCalled, false)
})

test('Glioma, Meningioma, and Pituitary Tumor each render MRI data and run stages 2/3', async () => {
  for (const className of ['Glioma', 'Meningioma', 'Pituitary Tumor']) {
    let clinicalCalled = false
    let idhCalled = false
    const scores = { 'No Tumor': 0.05, [className]: 0.85 }
    const result = await runBrainMultimodalPipeline(input(), dependencies({
      analyzeImage: async () => ({ kind: 'result', result: { ...tumorImageResult, prediction: className, classification: className, classScores: scores } }),
      analyzeClinical: async () => { clinicalCalled = true; return dependencies().analyzeClinical() },
      analyzeIdh: async () => { idhCalled = true; return idhResult },
    }))
    assert.equal(result.mri.status, 'success', className)
    assert.equal(result.mri.result.prediction, className)
    assert.deepEqual(result.mri.result.classScores, scores)
    assert.equal(getMRIScreeningDisplay(result.mri.result).prediction, className)
    assert.equal(clinicalCalled, true, className)
    assert.equal(idhCalled, true, className)
    assert.equal(result.clinical.status, 'success', className)
    assert.equal(result.idh.status, 'success', className)
  }
})

test('Stage 1 success progress carries its MRI result while later stages are pending', async () => {
  let resolveClinical
  const clinicalPending = new Promise((resolve) => { resolveClinical = resolve })
  let mriProgress
  const run = runBrainMultimodalPipeline(input(), dependencies({ analyzeClinical: async () => clinicalPending }), (stage, status, _message, result) => {
    if (stage === 'mri' && status === 'success') mriProgress = result
  })
  await new Promise((resolve) => setImmediate(resolve))
  assert.equal(mriProgress.prediction, 'Glioma')
  assert.deepEqual(mriProgress.classScores, tumorImageResult.classScores)
  resolveClinical(dependencies().analyzeClinical())
  await run
})

test('missing selected slice keeps actual MRI class and scores with preview fallback', () => {
  const display = getMRIScreeningDisplay({
    selectedSlice: undefined,
    prediction: 'Glioma',
    classification: 'Glioma',
    confidence: 0.85,
    classScores: { Glioma: 0.85, 'No Tumor': 0.15 },
    totalSlices: 1,
    tumorSlices: 1,
    selectedFileName: 'case.png',
  })
  assert.deepEqual(display, {
    prediction: 'Glioma', classification: 'Glioma', confidence: 0.85,
    classScores: { Glioma: 0.85, 'No Tumor': 0.15 }, previewAvailable: false,
    screeningLabel: 'Tumor Detected',
  })
})

test('wrapped clinical response maps correctly; missing scores preserve subtype', () => {
  const result = normalizeBrainClinicalStageResult({ clinicalResult: {
    predicted_subtype: 'OLIGODENDROGLIOMA', predicted_subtype_label: 'Oligodendroglioma',
  } })
  assert.equal(result.predictedSubtypeLabel, 'Oligodendroglioma')
  assert.equal(result.predictedSubtype, 'OLIGODENDROGLIOMA')
  assert.equal(result.classScores, null)
})

test('missing display label falls back to returned subtype identifier', () => {
  const result = normalizeBrainClinicalStageResult({ predictedSubtype: 'ASTROCYTOMA' })
  assert.equal(result.predictedSubtype, 'ASTROCYTOMA')
  assert.equal(result.predictedSubtypeLabel, null)
})

test('missing clinical result becomes a failed clinical stage while other stages succeed', async () => {
  const result = await runBrainMultimodalPipeline(input(), dependencies({ analyzeClinical: async () => undefined }))
  assert.equal(result.clinical.status, 'failed')
  assert.match(result.clinical.message, /no result object/i)
  assert.equal(result.mri.status, 'success')
  assert.equal(result.idh.status, 'success')
})

test('clinical inference failure does not suppress successful MRI or IDH results', async () => {
  const result = await runBrainMultimodalPipeline(input(), dependencies({
    analyzeClinical: async () => { throw new Error('clinical service unavailable') },
  }))
  assert.equal(result.clinical.status, 'failed')
  assert.match(result.clinical.message, /clinical service unavailable/i)
  assert.equal(result.mri.status, 'success')
  assert.equal(result.idh.status, 'success')
})

test('unprovided inputs leave the stages explicitly skipped', async () => {
  const result = await runBrainMultimodalPipeline(input({ files: [], clinical: null }), dependencies())
  assert.equal(result.mri.status, 'skipped')
  assert.equal(result.clinical.status, 'skipped')
  assert.equal(result.idh.status, 'skipped')
  assert.equal(result.clinical.message, 'Skipped because MRI screening did not produce a tumor classification.')
  assert.equal(result.idh.message, 'Skipped because MRI screening did not produce a tumor classification.')
})
