import { useState } from 'react'
import type { FormEvent } from 'react'

import { useAppDispatch } from '../../app/hooks'
import { useCreateResearchMutation } from '../../features/research/researchApi'
import { closeSidebar, selectRun } from '../../features/research/researchSlice'
import { getErrorMessage } from '../../utils/format'

function ResearchForm() {
  const dispatch = useAppDispatch()
  const [query, setQuery] = useState('Research the impact of AI in healthcare in 2025')
  const [maxTasks, setMaxTasks] = useState(3)
  const [createResearch, { isLoading, error }] = useCreateResearchMutation()

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const clampedTasks = Math.min(Math.max(Math.trunc(maxTasks) || 1, 1), 8)
    try {
      const created = await createResearch({ query, max_tasks: clampedTasks }).unwrap()
      if (created.research_id != null) {
        dispatch(selectRun(created.research_id))
      }
      dispatch(closeSidebar())
    } catch {
      // Error surfaced via the `error` state below.
    }
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

        {error ? (
          <p className="form-error">{getErrorMessage(error, 'Research request failed.')}</p>
        ) : null}
      </form>
    </section>
  )
}

export default ResearchForm
