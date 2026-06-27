import type { Source } from '../../features/research/types'

type SourcesGridProps = {
  sources: Source[]
}

function SourcesGrid({ sources }: SourcesGridProps) {
  return (
    <section className="card">
      <h2>Sources</h2>
      {sources.length === 0 ? (
        <p className="muted">No sources were gathered for this run.</p>
      ) : (
        <div className="source-grid">
          {sources.map((source) => (
            <article className="source-card" key={`${source.url}-${source.citation_id}`}>
              <div className="source-header">
                <span className="citation">[{source.citation_id ?? '-'}]</span>
                <span className={`pill reliability-${source.reliability}`}>{source.reliability}</span>
                <span className="pill">{source.source_type}</span>
              </div>
              <h3>{source.title}</h3>
              <p>{source.snippet || 'No snippet available.'}</p>
              {source.url ? (
                <a href={source.url} target="_blank" rel="noreferrer">
                  Open source ↗
                </a>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default SourcesGrid
