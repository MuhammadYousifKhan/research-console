type ErrorBannerProps = {
  message: string
  onDismiss?: () => void
}

function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  if (!message) return null
  return (
    <div className="error-banner" role="alert">
      <span className="bang" aria-hidden="true">
        !
      </span>
      <span>{message}</span>
      {onDismiss ? (
        <button type="button" className="error-dismiss" onClick={onDismiss} aria-label="Dismiss error">
          ×
        </button>
      ) : null}
    </div>
  )
}

export default ErrorBanner
