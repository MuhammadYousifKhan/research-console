import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { closeSidebar } from '../../features/research/researchSlice'
import HistoryList from '../research/HistoryList'
import ResearchForm from '../research/ResearchForm'

function Sidebar() {
  const dispatch = useAppDispatch()
  const sidebarOpen = useAppSelector((state) => state.researchUi.sidebarOpen)

  return (
    <>
      <div
        className={`sidebar-backdrop ${sidebarOpen ? 'visible' : ''}`}
        onClick={() => dispatch(closeSidebar())}
        aria-hidden="true"
      />
      <aside className={`left-column ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-head">
          <h2>Console</h2>
          <button
            type="button"
            className="ghost sidebar-close"
            onClick={() => dispatch(closeSidebar())}
            aria-label="Close navigation"
          >
            ×
          </button>
        </div>
        <ResearchForm />
        <HistoryList />
      </aside>
    </>
  )
}

export default Sidebar
