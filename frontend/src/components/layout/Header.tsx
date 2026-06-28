import { useAppDispatch } from '../../app/hooks'
import { toggleSidebar } from '../../features/research/researchSlice'

function Header() {
  const dispatch = useAppDispatch()

  return (
    <header className="hero-bar">
      <div className="hero-title">
        <p className="eyebrow">Autonomous Research Agent</p>
        <h1>Research Console</h1>
        <p className="subtitle">
          Launch a run, watch the five-stage pipeline, and read the cited, evaluated answer.
          The console reports real state — failures included.
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
