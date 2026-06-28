import { useAppSelector } from '../../app/hooks'
import { useGetRunQuery } from '../../features/research/researchApi'
import Timeline from './Timeline'

/**
 * Renders the selected run's pipeline in the sidebar. Reuses the same cached
 * `getRun` query as the workspace, so it triggers no extra network request.
 */
function PipelineCard() {
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const { data: run } = useGetRunQuery(selectedRunId as number, {
    skip: selectedRunId == null,
  })

  if (!run || run.steps.length === 0) {
    return null
  }

  return <Timeline steps={run.steps} />
}

export default PipelineCard
