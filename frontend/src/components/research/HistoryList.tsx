import { useEffect, useRef } from 'react'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { useGetHistoryQuery } from '../../features/research/researchApi'
import { closeSidebar, selectRun } from '../../features/research/researchSlice'
import type { ResearchHistoryItem } from '../../features/research/types'
import { formatDateTime, getErrorMessage } from '../../utils/format'

// The card shows only the most recent runs; the rest live behind "View full
// history" so the sidebar card doesn't grow without bound.
const PREVIEW_COUNT = 6

function HistoryList() {
  const dispatch = useAppDispatch()
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  // Fetch the full list (backend caps at 100); the card itself only previews it.
  const { data, isLoading, isFetching, error, refetch } = useGetHistoryQuery(100)
  const dialogRef = useRef<HTMLDialogElement>(null)

  const items = data?.items ?? []
  const firstRunId = items[0]?.research_id
  const previewItems = items.slice(0, PREVIEW_COUNT)
  const hasMore = items.length > PREVIEW_COUNT

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

  function onSelectFromDialog(id: number) {
    onSelect(id)
    dialogRef.current?.close()
  }

  const renderList = (list: ResearchHistoryItem[], onPick: (id: number) => void) => (
    <ul className="history-list">
      {list.map((item) => (
        <li key={item.research_id}>
          <button
            type="button"
            onClick={() => onPick(item.research_id)}
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
  )

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

      {renderList(previewItems, onSelect)}

      {hasMore ? (
        <button
          type="button"
          className="ghost history-view-all"
          onClick={() => dialogRef.current?.showModal()}
        >
          View full history ({items.length})
        </button>
      ) : null}

      <dialog
        ref={dialogRef}
        className="history-dialog"
        // Close when the backdrop (the dialog element itself) is clicked.
        onClick={(event) => {
          if (event.target === dialogRef.current) dialogRef.current?.close()
        }}
      >
        <div className="history-dialog-inner">
          <div className="history-dialog-head">
            <div className="card-eyebrow muted-eyebrow">Full history ({items.length})</div>
            <button
              type="button"
              className="ghost sidebar-close"
              onClick={() => dialogRef.current?.close()}
              aria-label="Close full history"
            >
              ×
            </button>
          </div>
          <div className="history-dialog-body">{renderList(items, onSelectFromDialog)}</div>
        </div>
      </dialog>
    </section>
  )
}

export default HistoryList
