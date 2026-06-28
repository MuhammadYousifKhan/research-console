import { useAppSelector } from '../../app/hooks'
import { useGetRunQuery } from '../../features/research/researchApi'
import { getErrorMessage } from '../../utils/format'
import AnswerCard from './AnswerCard'
import CitationsCard from './CitationsCard'
import EmptyState from './EmptyState'
import ErrorBanner from './ErrorBanner'
import RunOverview from './RunOverview'
import SourcesGrid from './SourcesGrid'

function ResearchWorkspace() {
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const { data: run, isLoading, isFetching, error } = useGetRunQuery(selectedRunId as number, {
    skip: selectedRunId == null,
  })

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
