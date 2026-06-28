import { Fragment, type ReactNode } from 'react'

import type { Evaluation } from '../../features/research/types'
import type { AnswerBlock, InlineSpan } from '../../utils/format'
import { confidenceLabel, parseAnswerBlocks } from '../../utils/format'

type AnswerCardProps = {
  answer: string
  evaluation: Evaluation
}

function renderSpans(spans: InlineSpan[]) {
  return spans.map((span, index) =>
    span.bold ? (
      <strong key={index}>{span.text}</strong>
    ) : (
      <Fragment key={index}>{span.text}</Fragment>
    ),
  )
}

/** Group the flat block list so consecutive list items render inside one <ul>. */
function renderBlocks(blocks: AnswerBlock[]) {
  const out: ReactNode[] = []
  let bullets: AnswerBlock[] = []

  const flushBullets = () => {
    if (bullets.length === 0) return
    out.push(
      <ul key={`ul-${out.length}`} className="answer-list">
        {bullets.map((item, index) => (
          <li key={index}>{renderSpans(item.spans)}</li>
        ))}
      </ul>,
    )
    bullets = []
  }

  blocks.forEach((block) => {
    if (block.kind === 'li') {
      bullets.push(block)
      return
    }
    flushBullets()
    if (block.kind === 'h') {
      const key = `h-${out.length}`
      out.push(
        block.level === 2 ? (
          <h3 key={key}>{renderSpans(block.spans)}</h3>
        ) : (
          <h4 key={key}>{renderSpans(block.spans)}</h4>
        ),
      )
    } else {
      out.push(<p key={`p-${out.length}`}>{renderSpans(block.spans)}</p>)
    }
  })
  flushBullets()
  return out
}

function AnswerCard({ answer, evaluation }: AnswerCardProps) {
  const blocks = parseAnswerBlocks(answer)
  const supported = evaluation.is_supported

  return (
    <div className="answer-card">
      <div className="answer-head">
        <div className="answer-eyebrow">Synthesized answer</div>
        <span className={`confidence confidence-${evaluation.confidence}`}>
          {confidenceLabel(evaluation.confidence)}
        </span>
      </div>

      <div className="answer-text">
        {blocks.length > 0 ? (
          renderBlocks(blocks)
        ) : (
          <p className="muted">No answer text was produced.</p>
        )}
      </div>

      <div className={`evaluation-box ${supported ? 'supported' : 'unsupported'}`}>
        <div className="eval-pills">
          <span className={`status-pill support-pill ${supported ? 'yes' : 'no'}`}>
            {supported ? 'Supported by evidence' : 'Not fully supported'}
          </span>
          <span className={`confidence confidence-${evaluation.confidence}`}>
            {confidenceLabel(evaluation.confidence)}
          </span>
        </div>

        {evaluation.notes ? <p className="eval-notes">{evaluation.notes}</p> : null}

        {evaluation.missing_evidence.length > 0 ? (
          <>
            <div className="eval-missing-title">Missing evidence</div>
            <div className="eval-missing">
              {evaluation.missing_evidence.map((item, index) => (
                <div className="eval-missing-item" key={`missing-${index}`}>
                  <span className="dash">—</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

export default AnswerCard
