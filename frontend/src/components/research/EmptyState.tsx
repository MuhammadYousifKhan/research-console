type EmptyStateProps = {
  isLoading?: boolean
}

function EmptyState({ isLoading }: EmptyStateProps) {
  return (
    <section className="card empty-state">
      <h2>{isLoading ? 'Loading research…' : 'No Active Research'}</h2>
      <p>
        {isLoading
          ? 'Fetching the latest run from the server.'
          : 'Start a research run from the panel. You will see task steps, cleaned sources, the synthesized answer, and support evaluation here.'}
      </p>
    </section>
  )
}

export default EmptyState
