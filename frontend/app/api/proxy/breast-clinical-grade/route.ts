export const runtime = 'nodejs'

export async function POST(request: Request) {
  const baseUrl = (process.env.BREAST_GRADE_API_URL || 'http://127.0.0.1:8003').replace(/\/$/, '')
  try {
    const upstream = await fetch(`${baseUrl}/api/v1/analysis/breast-clinical-grade`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: await request.text(),
      cache: 'no-store',
    })
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return Response.json(
      { detail: 'Balanced clinical-grade API is not reachable. Start it on port 8003.' },
      { status: 503 },
    )
  }
}
