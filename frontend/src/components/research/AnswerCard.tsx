import type { Evaluation } from '../../features/research/types'
import { confidenceLabel } from '../../utils/format'

type AnswerCardProps = {
  answer: string
  evaluation: Evaluation
}

function AnswerCard({ answer, evaluation }: AnswerCardProps) {
  const paragraphs = answer.split('\n').filter((line) => line.trim().length > 0)

  return (
    <section className="card answer-card">
      <div className="answer-head">
        <h2>Final Answer</h2>
        <span className={`confidence confidence-${evaluation.confidence}`}>
          {confidenceLabel(evaluation.confidence)}
        </span>
      </div>

      <div className="answer-text">
        {paragraphs.length > 0 ? (
          paragraphs.map((line, index) => <p key={`answer-${index}`}>{line}</p>)
        ) : (
          <p className="muted">No answer text was produced.</p>
        )}
      </div>

      <div className="evaluation-box">
        <p>
          <strong>Supported by evidence:</strong>{' '}
          <span className={evaluation.is_supported ? 'tag-yes' : 'tag-no'}>
            {evaluation.is_supported ? 'Yes' : 'No'}
          </span>
        </p>
        {evaluation.notes ? <p className="muted">{evaluation.notes}</p> : null}
        {evaluation.missing_evidence.length > 0 ? (
          <>
            <p>
              <strong>Missing evidence:</strong>
            </p>
            <ul>
              {evaluation.missing_evidence.map((item, index) => (
                <li key={`missing-${index}`}>{item}</li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    </section>
  )
}

export default AnswerCard
