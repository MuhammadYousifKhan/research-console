import { useEffect } from 'react'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { useGetHistoryQuery } from '../../features/research/researchApi'
import { closeSidebar, selectRun } from '../../features/research/researchSlice'
import { formatDateTime, getErrorMessage } from '../../utils/format'

function HistoryList() {
  const dispatch = useAppDispatch()
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const { data, isLoading, isFetching, error, refetch } = useGetHistoryQuery(30)

  const items = data?.items ?? []
  const firstRunId = items[0]?.research_id

  // Auto-select the most recent run on first load so the panel isn't empty.
  useEffect(() => {
    if (selectedRunId == null && firstRunId != null) {
      dispatch(selectRun(firstRunId))
    }
  }, [dispatch, selectedRunId, firstRunId])

  function onSelect(id: number) {
    dispatch(selectRun(id))
    dispatch(closeSidebar())
  }

  return (
    <section className="card history-card">
      <div className="section-title-row">
        <div className="card-eyebrow muted-eyebrow">History</div>
        <button
          type="button"
          className="ghost icon-refresh"
          onClick={() => void refetch()}
          disabled={isFetching}
          title="Refresh"
          aria-label="Refresh history"
        >
          ↻
        </button>
      </div>

      {isLoading ? <p className="muted">Loading history…</p> : null}
      {error ? <p className="form-error">{getErrorMessage(error, 'Failed to load history.')}</p> : null}
      {!isLoading && !error && items.length === 0 ? (
        <p className="muted">No previous research runs found.</p>
      ) : null}

      <ul className="history-list">
        {items.map((item) => (
          <li key={item.research_id}>
            <button
              type="button"
              onClick={() => onSelect(item.research_id)}
              className={selectedRunId === item.research_id ? 'active' : ''}
            >
              <span className="history-row">
                <span className="dot completed" aria-hidden="true" />
                <strong>{item.query}</strong>
              </span>
              <span className="history-meta">
                <span>{formatDateTime(item.created_at)}</span>
                <span className="sep">·</span>
                <span>#{item.research_id}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}

export default HistoryList
