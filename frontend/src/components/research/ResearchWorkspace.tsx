import { useAppSelector } from '../../app/hooks'
import { useGetRunQuery } from '../../features/research/researchApi'
import { getErrorMessage } from '../../utils/format'
import AnswerCard from './AnswerCard'
import EmptyState from './EmptyState'
import ErrorBanner from './ErrorBanner'
import RunOverview from './RunOverview'
import SourcesGrid from './SourcesGrid'
import Timeline from './Timeline'

function ResearchWorkspace() {
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const { data: run, isLoading, isFetching, error } = useGetRunQuery(selectedRunId as number, {
    skip: selectedRunId == null,
  })

  if (selectedRunId == null) {
    return <EmptyState />
  }

  if (error) {
    return <ErrorBanner message={getErrorMessage(error, 'Failed to load the research run.')} />
  }

  if (!run || isLoading) {
    return <EmptyState isLoading />
  }

  return (
    <div className={`workspace ${isFetching ? 'is-refreshing' : ''}`}>
      <RunOverview run={run} />
      <Timeline steps={run.steps} />
      <SourcesGrid sources={run.sources} />
      <AnswerCard answer={run.answer} evaluation={run.evaluation} />
    </div>
  )
}

export default ResearchWorkspace
