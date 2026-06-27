import type { ExecutionStep } from '../../features/research/types'

type TimelineProps = {
  steps: ExecutionStep[]
}

function Timeline({ steps }: TimelineProps) {
  return (
    <section className="card">
      <h2>Task Timeline</h2>
      <ol className="timeline">
        {steps.map((step, index) => (
          <li key={`${step.name}-${index}`}>
            <div className={`dot ${step.status}`} aria-hidden="true" />
            <div className="timeline-body">
              <div className="timeline-row">
                <h3>{step.name.replace(/_/g, ' ')}</h3>
                <span className={`status-pill status-${step.status}`}>{step.status}</span>
              </div>
              <p>{step.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}

export default Timeline
