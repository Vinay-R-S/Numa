import { NextRequest, NextResponse } from "next/server"

/** FastAPI backend - always on the same machine the Next.js server is running on. */
const BACKEND = process.env.BACKEND_URL ?? "http://127.0.0.1:8000"

/**
 * Catch-all proxy: forwards  /api/<anything>  →  BACKEND/<anything>
 * Handles every HTTP method (GET, POST, PUT, PATCH, DELETE, OPTIONS).
 */
async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  const backendPath = "/" + path.join("/")

  // Rebuild the query string (if any)
  const qs = req.nextUrl.search ?? ""

  // Forward the body for non-GET/HEAD requests
  const hasBody = !["GET", "HEAD"].includes(req.method)
  const body = hasBody ? await req.arrayBuffer() : undefined

  // Build headers - forward content-type + auth, drop host / connection
  const headers = new Headers()
  const ct = req.headers.get("content-type")
  if (ct) headers.set("content-type", ct)
  const auth = req.headers.get("authorization")
  if (auth) headers.set("authorization", auth)

  let upstream: Response
  try {
    upstream = await fetch(`${BACKEND}${backendPath}${qs}`, {
      method: req.method,
      headers,
      body: body && body.byteLength > 0 ? body : undefined,
    })
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown fetch error"
    return NextResponse.json(
      {
        detail: `Backend unavailable at ${BACKEND}. ${message}`,
      },
      { status: 503 }
    )
  }

  // Stream the response back with the same status + content-type
  const resHeaders = new Headers()
  const resCt = upstream.headers.get("content-type")
  if (resCt) resHeaders.set("content-type", resCt)

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: resHeaders,
  })
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const PATCH = handler
export const DELETE = handler
export const OPTIONS = handler
