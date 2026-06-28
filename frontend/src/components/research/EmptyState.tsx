type EmptyStateProps = {
  isLoading?: boolean
}

function EmptyState({ isLoading }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="glyph" aria-hidden="true">
        ?
      </div>
      <h2>{isLoading ? 'Loading research…' : 'No run selected'}</h2>
      <p>
        {isLoading
          ? 'Fetching the latest run from the server.'
          : 'Submit a research question on the left, or open a past run from history.'}
      </p>
    </div>
  )
}

export default EmptyState
