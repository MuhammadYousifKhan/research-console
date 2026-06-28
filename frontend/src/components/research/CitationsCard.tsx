import { useMemo, useState } from 'react'

import { useGetCitationsQuery } from '../../features/research/researchApi'
import type { CitationStyle } from '../../features/research/types'

type CitationsCardProps = {
  researchId: number
  hasSources: boolean
  className?: string
}

const STYLE_LABELS: Record<CitationStyle, string> = {
  apa: 'APA',
  mla: 'MLA',
  ieee: 'IEEE',
  harvard: 'Harvard',
  chicago: 'Chicago',
  bibtex: 'BibTeX',
}

const STYLE_ORDER: CitationStyle[] = ['apa', 'mla', 'ieee', 'harvard', 'chicago', 'bibtex']

function CitationsCard({ researchId, hasSources, className = '' }: CitationsCardProps) {
  const [style, setStyle] = useState<CitationStyle>('apa')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const { data, isLoading, isError } = useGetCitationsQuery(researchId, {
    skip: !hasSources,
  })

  const items = useMemo(() => data?.styles[style] ?? [], [data, style])

  if (!hasSources) {
    return null
  }

  const copy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      window.setTimeout(() => setCopiedKey((current) => (current === key ? null : current)), 1500)
    } catch {
      // Clipboard can be unavailable (e.g. insecure context); fail silently.
    }
  }

  const copyAll = () => {
    const all = items.map((item) => item.text).join('\n\n')
    void copy(all, 'all')
  }

  return (
    <section className={`citations ${className}`.trim()}>
      <div className="sources-head citations-head">
        <span className="label">Citations</span>
        {data ? <span className="count">{items.length}</span> : null}
        {data?.accessed ? (
          <span className="citations-accessed">accessed {data.accessed}</span>
        ) : null}
      </div>

      <div className="citations-toolbar">
        <div className="citations-styles" role="group" aria-label="Citation style">
          {STYLE_ORDER.map((key) =>
            style === key ? (
              <button
                key={key}
                type="button"
                aria-pressed="true"
                className="citations-style active"
                onClick={() => setStyle(key)}
              >
                {STYLE_LABELS[key]}
              </button>
            ) : (
              <button
                key={key}
                type="button"
                aria-pressed="false"
                className="citations-style"
                onClick={() => setStyle(key)}
              >
                {STYLE_LABELS[key]}
              </button>
            ),
          )}
        </div>
        {items.length > 0 ? (
          <button type="button" className="citations-copy-all" onClick={copyAll}>
            {copiedKey === 'all' ? 'Copied ✓' : 'Copy all'}
          </button>
        ) : null}
      </div>

      {isLoading ? (
        <p className="muted">Building citations…</p>
      ) : isError ? (
        <p className="muted">Citations could not be generated for this run.</p>
      ) : items.length === 0 ? (
        <p className="muted">No sources are available to cite.</p>
      ) : (
        <ol className="citations-list">
          {items.map((item, index) => {
            const key = `${style}-${item.citation_id ?? index}`
            return (
              <li key={key} className="citation-row">
                <span className="citation-marker">[{item.citation_id ?? index + 1}]</span>
                <p className="citation-text">{item.text}</p>
                <button
                  type="button"
                  className="citation-copy"
                  onClick={() => copy(item.text, key)}
                >
                  {copiedKey === key ? 'Copied ✓' : 'Copy'}
                </button>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}

export default CitationsCard
