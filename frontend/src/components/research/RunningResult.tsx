import { useAppSelector } from '../../app/hooks'

// Varying widths keep the shimmer placeholders from looking like a solid block.
const ANSWER_BARS = ['96%', '88%', '92%', '70%', '83%']
const SOURCE_CARD_BARS = ['60%', '100%', '90%', '45%']
const SOURCE_CARD_COUNT = 3

/**
 * Workspace body shown while a run is streaming. It mirrors the shape of the
 * finished result — a run header, a synthesized-answer card, and a sources
 * grid — but fills each region with live progress and shimmer skeletons so the
 * whole console reacts to "Run research", not just the button.
 *
 * The live pipeline itself renders in the sidebar via PipelineCard.
 */
function RunningResult() {
  const query = useAppSelector((state) => state.researchUi.streamQuery)
  const maxTasks = useAppSelector((state) => state.researchUi.streamMaxTasks)
  const liveSteps = useAppSelector((state) => state.researchUi.liveSteps)

  const stepsDone = liveSteps.length
  const anyFailed = liveSteps.some((step) => step.status === 'failed')

  return (
    <>
      <div className="workspace-main">
        <section className="run-overview">
          <div className="run-overview-eyebrow">Research run · live</div>
          <h2>{query || 'Running research…'}</h2>

          <div className="metrics">
            <article>
              <div className="m-label">Tasks</div>
              <div className="m-value">{maxTasks || '—'}</div>
              <div className="m-sub">planned</div>
            </article>
            <article>
              <div className="m-label">Steps</div>
              <div className="m-value">{stepsDone}</div>
              <div className={`m-sub ${anyFailed ? 'fail' : ''}`}>in progress</div>
            </article>
            <article>
              <div className="m-label">Sources</div>
              <div className="m-value">—</div>
              <div className="m-sub">gathering</div>
            </article>
          </div>
        </section>

        <div className="answer-card">
          <div className="running-head">
            <span className="pulse" aria-hidden="true" />
            <span>Synthesizing answer…</span>
          </div>
          <div className="skeleton-bars" aria-hidden="true">
            {ANSWER_BARS.map((width, index) => (
              <div key={index} className="skeleton-bar" style={{ width }} />
            ))}
          </div>
        </div>
      </div>

      <section className="full-span">
        <div className="sources-head">
          <span className="label">Sources</span>
          <span className="count">gathering</span>
        </div>
        <div className="source-grid" aria-hidden="true">
          {Array.from({ length: SOURCE_CARD_COUNT }).map((_, cardIndex) => (
            <div className="source-card" key={cardIndex}>
              <div className="skeleton-bars">
                {SOURCE_CARD_BARS.map((width, barIndex) => (
                  <div key={barIndex} className="skeleton-bar" style={{ width }} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  )
}

export default RunningResult
