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
