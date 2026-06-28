import type { Source } from '../../features/research/types'
import { hostFromUrl } from '../../utils/format'

type SourcesGridProps = {
  sources: Source[]
  className?: string
}

function SourcesGrid({ sources, className = '' }: SourcesGridProps) {
  return (
    <section className={className}>
      <div className="sources-head">
        <span className="label">Sources</span>
        <span className="count">{sources.length}</span>
      </div>

      {sources.length === 0 ? (
        <p className="muted">No sources were gathered for this run.</p>
      ) : (
        <div className="source-grid">
          {sources.map((source) => {
            const host = hostFromUrl(source.url)
            const card = (
              <>
                <div className="source-top">
                  <span className="citation">[{source.citation_id ?? '-'}]</span>
                  <span className={`pill reliability-${source.reliability}`}>{source.reliability}</span>
                </div>
                <h3>{source.title}</h3>
                {host ? <div className="source-host">{host}</div> : null}
                <p className="source-snippet">{source.snippet || 'No snippet available.'}</p>
                <div className="source-foot">
                  <span className="source-type">{source.source_type}</span>
                  {source.url ? <span className="source-open">open ↗</span> : null}
                </div>
              </>
            )

            return source.url ? (
              <a
                className="source-card"
                key={`${source.url}-${source.citation_id}`}
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                {card}
              </a>
            ) : (
              <div className="source-card" key={`${source.title}-${source.citation_id}`}>
                {card}
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default SourcesGrid
