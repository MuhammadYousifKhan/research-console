import { API_BASE_URL } from './researchApi'
import type { CreateResearchRequest, ExecutionStep, ResearchRun } from './types'

type StreamHandlers = {
  onStep: (step: ExecutionStep) => void
  onComplete: (run: ResearchRun) => void
  onError: (message: string) => void
}

type StreamEvent =
  | { type: 'step'; step: ExecutionStep }
  | { type: 'complete'; run: ResearchRun }
  | { type: 'error'; message?: string }

/**
 * POST a research request and consume the Server-Sent Events stream from
 * `/research/stream`, invoking the handlers as each pipeline stage arrives.
 *
 * Uses `fetch` + a ReadableStream reader (rather than `EventSource`) so the
 * query travels in the request body and the stream is not auto-reconnected
 * after completion.
 */
export async function streamResearch(
  body: CreateResearchRequest,
  handlers: StreamHandlers,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/research/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch {
    handlers.onError('Could not reach the research service.')
    return
  }

  if (!response.ok || !response.body) {
    handlers.onError(`Research request failed (${response.status}).`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE frames are separated by a blank line; keep the trailing partial.
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''

    for (const frame of frames) {
      const dataLine = frame.split('\n').find((line) => line.startsWith('data:'))
      if (!dataLine) continue
      const payload = dataLine.slice(5).trim()
      if (!payload) continue

      let event: StreamEvent
      try {
        event = JSON.parse(payload) as StreamEvent
      } catch {
        continue
      }

      if (event.type === 'step') handlers.onStep(event.step)
      else if (event.type === 'complete') handlers.onComplete(event.run)
      else if (event.type === 'error') handlers.onError(event.message ?? 'The research run failed.')
    }
  }
}
