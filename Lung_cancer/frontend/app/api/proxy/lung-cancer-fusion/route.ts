export const runtime = 'nodejs'

export async function POST(request: Request) {
  const baseUrl = (process.env.LUNG_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001').replace(/\/$/, '')
  try {
    const formData = await request.formData()
    const upstream = await fetch(`${baseUrl}/api/v1/analysis/lung-cancer-fusion`, {
      method: 'POST',
      body: formData,
      cache: 'no-store',
    })
    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return Response.json({ detail: 'The lung research API is not reachable. Make sure its server is running.' }, { status: 503 })
  }
}
