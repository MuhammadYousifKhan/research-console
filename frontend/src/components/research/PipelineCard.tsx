import { useAppSelector } from '../../app/hooks'
import { useGetRunQuery } from '../../features/research/researchApi'
import Timeline from './Timeline'

/**
 * Renders the pipeline in the sidebar. While a run is streaming it shows the
 * live steps as they arrive; otherwise it reuses the same cached `getRun`
 * query as the workspace, so it triggers no extra network request.
 */
function PipelineCard() {
  const selectedRunId = useAppSelector((state) => state.researchUi.selectedRunId)
  const streamStatus = useAppSelector((state) => state.researchUi.streamStatus)
  const liveSteps = useAppSelector((state) => state.researchUi.liveSteps)
  const { data: run } = useGetRunQuery(selectedRunId as number, {
    skip: selectedRunId == null,
  })

  // During a stream, surface progress immediately from the live steps.
  if (streamStatus === 'streaming' && liveSteps.length > 0) {
    return <Timeline steps={liveSteps} />
  }

  if (!run || run.steps.length === 0) {
    return null
  }

  return <Timeline steps={run.steps} />
}

export default PipelineCard
