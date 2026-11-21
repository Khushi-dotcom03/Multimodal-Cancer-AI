export const runtime = 'nodejs'

export async function POST(request: Request) {
  const baseUrl = (
    process.env.BREAST_MODULE3_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://127.0.0.1:8002'
  ).replace(/\/$/, '')

  try {
    const formData = await request.formData()
    const features = formData.get('features')
    if (typeof features !== 'string') return Response.json({ detail: 'Clinical features are missing.' }, { status: 422 })

    const [upstream, clinicalUpstream] = await Promise.all([
      fetch(`${baseUrl}/api/v1/analysis/breast-cancer-fusion`, {
      method: 'POST',
      body: formData,
      cache: 'no-store',
      }),
      fetch(`${(process.env.BREAST_GRADE_API_URL || 'http://127.0.0.1:8003').replace(/\/$/, '')}/api/v1/analysis/breast-clinical-grade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ features: JSON.parse(features) }),
        cache: 'no-store',
      }),
    ])
    const payload = await upstream.json()
    const clinical = await clinicalUpstream.json()
    if (!upstream.ok) return Response.json(payload, { status: upstream.status })
    if (!clinicalUpstream.ok) return Response.json(clinical, { status: clinicalUpstream.status })

    payload.clinicalResult = {
      status: clinical.status,
      predictedGrade: clinical.predictedGrade,
      predictedGradeLabel: clinical.predictedGradeLabel,
      gradeScores: clinical.gradeScores,
      message: clinical.message,
      disclaimer: clinical.disclaimer,
    }
    return Response.json(payload, { status: upstream.status })
  } catch {
    return Response.json(
      { detail: 'Module 3 API is not reachable. Start the current FastAPI app on port 8002 or set BREAST_MODULE3_API_URL.' },
      { status: 503 },
    )
  }
}
