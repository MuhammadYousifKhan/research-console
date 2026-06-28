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

export type InlineSpan = { text: string; bold: boolean }

export type AnswerBlock =
  | { kind: 'h'; level: 2 | 3; spans: InlineSpan[] }
  | { kind: 'p'; spans: InlineSpan[] }
  | { kind: 'li'; spans: InlineSpan[] }

/** Parse `**bold**` markup into styled inline spans. */
export function parseInline(text: string): InlineSpan[] {
  const spans: InlineSpan[] = []
  const regex = /\*\*(.+?)\*\*/g
  let last = 0
  let match: RegExpExecArray | null
  while ((match = regex.exec(text)) !== null) {
    if (match.index > last) {
      spans.push({ text: text.slice(last, match.index), bold: false })
    }
    spans.push({ text: match[1], bold: true })
    last = match.index + match[0].length
  }
  if (last < text.length) {
    spans.push({ text: text.slice(last), bold: false })
  }
  return spans.length > 0 ? spans : [{ text, bold: false }]
}

/**
 * Split a synthesized answer into heading / paragraph / list blocks.
 * Handles `#`–`######` headings, `*`/`-`/`•` bullets, and inline `**bold**`.
 * The text is normalized first so headings and bullets that the model emitted
 * inline (collapsed onto one line) are broken back onto their own lines.
 */
export function parseAnswerBlocks(answer: string): AnswerBlock[] {
  if (!answer.trim()) return []

  const normalized = answer
    .replace(/\r/g, '')
    // Break inline bullets ("… text * next item") onto their own lines.
    // A single `*` surrounded by spaces is a bullet; `**bold**` has no inner space.
    .replace(/\s\*\s+(?=\S)/g, '\n* ')
    // Push headings that follow other text onto a new line.
    .replace(/([^\n])\s*(#{1,6}\s+)/g, '$1\n$2')

  const blocks: AnswerBlock[] = []
  for (const raw of normalized.split('\n')) {
    const line = raw.trim()
    if (!line) continue

    const heading = line.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      blocks.push({
        kind: 'h',
        level: heading[1].length <= 2 ? 2 : 3,
        spans: parseInline(heading[2].trim()),
      })
      continue
    }

    const bullet = line.match(/^[*\-•]\s+(.*)$/)
    if (bullet) {
      blocks.push({ kind: 'li', spans: parseInline(bullet[1].trim()) })
      continue
    }

    blocks.push({ kind: 'p', spans: parseInline(line) })
  }
  return blocks
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
