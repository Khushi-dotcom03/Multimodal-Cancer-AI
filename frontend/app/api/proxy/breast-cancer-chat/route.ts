export const runtime = 'nodejs'

export async function POST(request: Request) {
  const baseUrl = (
    process.env.BREAST_AI_API_URL || 'http://127.0.0.1:8011'
  ).replace(/\/$/, '')

  try {
    const body = await request.json()

    const upstream = await fetch(`${baseUrl}/api/v1/breast-cancer/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    })

    return new Response(await upstream.arrayBuffer(), {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('content-type') || 'application/json',
      },
    })
  } catch {
    return Response.json(
      { detail: 'The Breast Cancer AI Assistant is not reachable. Make sure its backend server is running on port 8011.' },
      { status: 503 },
    )
  }
}
