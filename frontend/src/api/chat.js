import { getToken, logout } from '@/utils/auth'
import router from '@/router'

export async function streamChat(body, onEvent, { signal } = {}) {
  const baseURL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
  const response = await fetch(`${baseURL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${getToken() || ''}`
    },
    body: JSON.stringify(body),
    signal
  })
  // fetch bypasses Axios interceptors; handle expired sessions and HTTP errors here.
  if (response.status === 401) {
    logout()
    router.push('/login')
    throw new Error('Your session has expired. Please sign in again.')
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.message || `Request failed: HTTP ${response.status}`)
  }
  // Do not parse a regular JSON response as SSE, even when its HTTP status is 200.
  if (!response.headers.get('content-type')?.includes('text/event-stream') || !response.body) {
    throw new Error('The service did not return an SSE stream. Check the endpoint URL and backend logs.')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      // A disconnect before done/error must not mark a partial answer as complete.
      if (done) throw new Error('The connection ended without a completion event. Please ask again.')
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop()
      for (const block of blocks) {
        // The backend emits single-line data: JSON events; the first six characters are "data: ".
        const event = JSON.parse(block.slice(6))
        onEvent(event)
        if (event.type === 'done' || event.type === 'error') return
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
