import { useAppSelector } from '../../app/hooks'
import { useGetRunQuery } from '../../features/research/researchApi'
import { getErrorMessage } from '../../utils/format'
import AnswerCard from './AnswerCard'
import CitationsCard from './CitationsCard'
import EmptyState from './EmptyState'
import ErrorBanner from './ErrorBanner'
import RunningResult from './RunningResult'
import RunOverview from './RunOverview'
import SourcesGrid from './SourcesGrid'

function ResearchWorkspace() {
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const streamStatus = useAppSelector((state) => state.researchUi.streamStatus)
  const streamError = useAppSelector((state) => state.researchUi.streamError)
  const { data: run, isLoading, isFetching, error } = useGetRunQuery(selectedRunId as number, {
    skip: selectedRunId == null,
  })

  // A run is streaming: show the live running layout in place of whatever was
  // selected before, so the whole workspace reacts — not just the form button.
  if (streamStatus === 'streaming') {
    return <RunningResult />
  }

  // A fresh run failed before it produced a selectable result.
  if (streamStatus === 'error' && selectedRunId == null) {
    return (
      <div className="workspace-main">
        <ErrorBanner message={streamError ?? 'The research run failed.'} />
        <EmptyState />
      </div>
    )
  }

  if (selectedRunId == null) {
    return (
      <div className="workspace-main">
        <EmptyState />
      </div>
    )
  }

  if (error) {
    return (
      <div className="workspace-main">
        <ErrorBanner message={getErrorMessage(error, 'Failed to load the research run.')} />
      </div>
    )
  }

  if (!run || isLoading) {
    return (
      <div className="workspace-main">
        <EmptyState isLoading />
      </div>
    )
  }

  const dim = isFetching ? 'is-refreshing' : ''

  return (
    <>
      <div className={`workspace-main ${dim}`}>
        <RunOverview run={run} />
        <AnswerCard answer={run.answer} evaluation={run.evaluation} />
      </div>
      <SourcesGrid sources={run.sources} className={`full-span ${dim}`} />
      {run.research_id != null ? (
        <CitationsCard
          researchId={run.research_id}
          hasSources={run.sources.length > 0}
          className={`full-span ${dim}`}
        />
      ) : null}
    </>
  )
}

export default ResearchWorkspace
