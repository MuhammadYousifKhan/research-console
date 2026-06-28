import type { ResearchRun } from '../../features/research/types'

type RunOverviewProps = {
  run: ResearchRun
}

function RunOverview({ run }: RunOverviewProps) {
  const total = run.steps.length
  const completed = run.steps.filter((step) => step.status === 'completed').length
  const failed = run.steps.filter((step) => step.status === 'failed').length

  const stepsSub = failed > 0 ? `${failed} failed` : total > 0 ? 'all clear' : '—'
  const stepsSubClass = failed > 0 ? 'fail' : 'ok'

  return (
    <section className="run-overview">
      <div className="run-overview-eyebrow">Research run · {run.research_id ?? 'N/A'}</div>
      <h2>{run.query}</h2>

      <div className="metrics">
        <article>
          <div className="m-label">Tasks</div>
          <div className="m-value">{run.plan.length}</div>
          <div className="m-sub">planned</div>
        </article>
        <article>
          <div className="m-label">Steps</div>
          <div className="m-value">
            {completed} / {total}
          </div>
          <div className={`m-sub ${stepsSubClass}`}>{stepsSub}</div>
        </article>
        <article>
          <div className="m-label">Sources</div>
          <div className="m-value">{run.sources.length}</div>
          <div className="m-sub">classified</div>
        </article>
      </div>
    </section>
  )
}

export default RunOverview
