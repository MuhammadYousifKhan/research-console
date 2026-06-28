import type { Evaluation } from '../../features/research/types'
import { confidenceLabel, parseAnswerBlocks } from '../../utils/format'

type AnswerCardProps = {
  answer: string
  evaluation: Evaluation
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
          blocks.map((block, index) =>
            block.kind === 'h' ? (
              <h4 key={`blk-${index}`}>{block.text}</h4>
            ) : (
              <p key={`blk-${index}`}>{block.text}</p>
            ),
          )
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
