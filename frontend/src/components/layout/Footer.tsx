function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="dot" aria-hidden="true" />
          <span>Research Console</span>
        </div>
        <p className="footer-copy">© {year} · Autonomous Research Agent</p>
      </div>
    </footer>
  )
}

export default Footer
