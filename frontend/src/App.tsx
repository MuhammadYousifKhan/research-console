import './App.css'
import Footer from './components/layout/Footer'
import Header from './components/layout/Header'
import Sidebar from './components/layout/Sidebar'
import ResearchWorkspace from './components/research/ResearchWorkspace'

function App() {
  return (
    <div className="app-shell">
      <Header />
      <main className="content-grid">
        <Sidebar />
        <ResearchWorkspace />
      </main>
      <Footer />
    </div>
  )
}

export default App
