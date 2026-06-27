function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <strong>Research Console</strong>
          <span className="muted">Planning · Tools · Cleanup · Synthesis · Evaluation</span>
        </div>
        <p className="footer-copy muted">© {year} Autonomous Research AI Agent</p>
      </div>
    </footer>
  )
}

export default Footer
