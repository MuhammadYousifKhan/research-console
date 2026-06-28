import type { ExecutionStep } from '../../features/research/types'

type TimelineProps = {
  steps: ExecutionStep[]
}

function statusLabel(status: ExecutionStep['status']): string {
  return status === 'completed' ? 'Completed' : 'Failed'
}

function Timeline({ steps }: TimelineProps) {
  const lastIndex = steps.length - 1

  return (
    <aside className="pipeline">
      <div className="pipeline-title">Pipeline</div>
      {steps.map((step, index) => (
        <div className="pipeline-step" key={`${step.name}-${index}`}>
          <div className="pipeline-rail">
            <span className={`dot ${step.status}`} aria-hidden="true" />
            {index !== lastIndex ? (
              <span className={`pipeline-line ${step.status}`} aria-hidden="true" />
            ) : null}
          </div>
          <div className="pipeline-body">
            <div className="pipeline-head">
              <span className="pipeline-idx">{String(index + 1).padStart(2, '0')}</span>
              <span className="pipeline-name">{step.name.replace(/_/g, ' ')}</span>
              <span className={`status-pill status-${step.status}`}>{statusLabel(step.status)}</span>
            </div>
            <div className="pipeline-detail">{step.detail}</div>
          </div>
        </div>
      ))}
    </aside>
  )
}

export default Timeline
