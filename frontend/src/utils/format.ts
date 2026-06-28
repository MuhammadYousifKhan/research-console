import type { Confidence } from '../features/research/types'

export function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

export function confidenceLabel(confidence: Confidence): string {
  if (confidence === 'high') return 'High confidence'
  if (confidence === 'medium') return 'Medium confidence'
  return 'Low confidence'
}

/** Derive a clean hostname (no leading www.) from a source URL. */
export function hostFromUrl(url: string): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0]
  }
}

export type AnswerBlock = { kind: 'h' | 'p'; text: string }

/**
 * Split a synthesized answer into heading/paragraph blocks.
 * Lines starting with `## ` become headings; everything else is a paragraph.
 * Falls back to single-newline splitting when the text has no blank lines.
 */
export function parseAnswerBlocks(answer: string): AnswerBlock[] {
  if (!answer.trim()) return []
  const chunks = answer.includes('\n\n') ? answer.split('\n\n') : answer.split('\n')
  return chunks
    .map((raw) => raw.trim())
    .filter((raw) => raw.length > 0)
    .map((raw) => {
      const isHeading = raw.startsWith('## ') || raw.startsWith('# ')
      return {
        kind: isHeading ? 'h' : 'p',
        text: isHeading ? raw.replace(/^#{1,2}\s+/, '') : raw,
      } as AnswerBlock
    })
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === 'string') return error
  if (error && typeof error === 'object') {
    // RTK Query error shapes: FetchBaseQueryError | SerializedError
    const maybe = error as { data?: unknown; error?: string; message?: string; status?: number }
    if (typeof maybe.data === 'string' && maybe.data) return maybe.data
    if (maybe.data && typeof maybe.data === 'object') {
      const detail = (maybe.data as { detail?: string }).detail
      if (detail) return detail
    }
    if (maybe.error) return maybe.error
    if (maybe.message) return maybe.message
    if (maybe.status) return `Request failed (${maybe.status})`
  }
  return fallback
}
