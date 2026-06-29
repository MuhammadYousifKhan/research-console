import { useState } from 'react'
import type { FormEvent } from 'react'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { researchApi } from '../../features/research/researchApi'
import {
  closeSidebar,
  selectRun,
  streamCompleted,
  streamFailed,
  streamStarted,
  streamStepReceived,
} from '../../features/research/researchSlice'
import { streamResearch } from '../../features/research/streamResearch'

function ResearchForm() {
  const dispatch = useAppDispatch()
  const [query, setQuery] = useState('Research the impact of AI in healthcare in 2025')
  const [maxTasks, setMaxTasks] = useState(3)
  const streamStatus = useAppSelector((state) => state.researchUi.streamStatus)
  const streamError = useAppSelector((state) => state.researchUi.streamError)
  const isLoading = streamStatus === 'streaming'

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isLoading) return
    const clampedTasks = Math.min(Math.max(Math.trunc(maxTasks) || 1, 1), 8)

    dispatch(streamStarted({ query, maxTasks: clampedTasks }))
    await streamResearch(
      { query, max_tasks: clampedTasks },
      {
        onStep: (step) => dispatch(streamStepReceived(step)),
        onComplete: (run) => {
          if (run.research_id != null) {
            dispatch(selectRun(run.research_id))
          }
          // The new run belongs in the history list; refetch it.
          dispatch(researchApi.util.invalidateTags([{ type: 'History', id: 'LIST' }]))
          dispatch(streamCompleted())
          dispatch(closeSidebar())
        },
        onError: (message) => dispatch(streamFailed(message)),
      },
    )
  }

  return (
    <section className="card form-card">
      <div className="card-eyebrow">New run</div>
      <form onSubmit={onSubmit}>
        <label htmlFor="query">Research question</label>
        <textarea
          id="query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          rows={4}
          required
          minLength={3}
          placeholder="What should the agent research?"
        />

        <div className="form-row">
          <div className="field-max">
            <label htmlFor="tasks">Max tasks</label>
            <input
              id="tasks"
              type="number"
              min={1}
              max={8}
              value={maxTasks}
              onChange={(event) => setMaxTasks(Number(event.target.value))}
            />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Running…' : 'Run research →'}
          </button>
        </div>

        {streamStatus === 'error' && streamError ? (
          <p className="form-error">{streamError}</p>
        ) : null}
      </form>
    </section>
  )
}

export default ResearchForm
