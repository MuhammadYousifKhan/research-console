import type { ResearchRun } from '../../features/research/types'

type RunOverviewProps = {
  run: ResearchRun
}

function RunOverview({ run }: RunOverviewProps) {
  const metrics = [
    { label: 'Tasks', value: run.plan.length },
    { label: 'Steps', value: run.steps.length },
    { label: 'Sources', value: run.sources.length },
  ]

  return (
    <section className="card run-overview">
      <div className="run-overview-head">
        <h2>{run.query}</h2>
        <p className="muted">Research ID: {run.research_id ?? 'N/A'}</p>
      </div>
      <div className="metrics">
        {metrics.map((metric) => (
          <article key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
          </article>
        ))}
      </div>
    </section>
  )
}

export default RunOverview
