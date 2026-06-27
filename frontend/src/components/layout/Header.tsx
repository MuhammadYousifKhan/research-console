import { useAppDispatch } from '../../app/hooks'
import { toggleSidebar } from '../../features/research/researchSlice'

function Header() {
  const dispatch = useAppDispatch()

  return (
    <header className="hero-bar">
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

      <div className="hero-title">
        <p className="eyebrow">Autonomous Research AI Agent</p>
        <h1>Research Console</h1>
        <p className="subtitle">
          Multi-step research orchestration with planning, tool execution, evidence cleanup,
          synthesis, and support evaluation.
        </p>
      </div>
    </header>
  )
}

export default Header
