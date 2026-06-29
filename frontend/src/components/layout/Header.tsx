import { useAppDispatch } from '../../app/hooks'
import { toggleSidebar } from '../../features/research/researchSlice'

function Header() {
  const dispatch = useAppDispatch()

  return (
    <header className="hero-bar">
      <div className="hero-title">
        <p className="eyebrow">An Autonomous AI Research Agent</p>
        <h1>Axiom</h1>
        <p className="subtitle">
          Launch a run, watch the six-stage pipeline, and read the cited, evaluated answer.
          Axiom reports real state — failures included.
        </p>
      </div>

      <button
        type="button"
        className="menu-toggle"
        onClick={() => dispatch(toggleSidebar())}
        aria-label="Toggle navigation"
      >
        <span />
        <span />
        <span />
      </button>
    </header>
  )
}

export default Header
