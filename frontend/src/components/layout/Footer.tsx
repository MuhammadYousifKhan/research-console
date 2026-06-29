function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="app-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <span className="dot" aria-hidden="true" />
          <span>Axiom</span>
        </div>
        <p className="footer-copy">© {year} · Axiom · An Autonomous AI Research Agent</p>
      </div>
    </footer>
  )
}

export default Footer
