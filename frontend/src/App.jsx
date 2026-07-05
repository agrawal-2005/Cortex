import { Routes, Route, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import { ToastProvider } from './components/Toast'
import Dashboard from './pages/Dashboard'
import Sources from './pages/Sources'
import Skills from './pages/Skills'
import SkillDetail from './pages/SkillDetail'
import ReviewQueue from './pages/ReviewQueue'
import Query from './pages/Query'
import DataOverview from './pages/DataOverview'
import Settings from './pages/Settings'

function App() {
  const location = useLocation()
  return (
    <ToastProvider>
      <div className="min-h-screen bg-bg">
        <Sidebar />
        <main className="pl-16 md:pl-60">
          {/* key on pathname re-triggers the page-enter transition */}
          <div key={location.pathname} className="page-enter max-w-6xl mx-auto px-6 lg:px-10 py-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/query" element={<Query />} />
              <Route path="/skills" element={<Skills />} />
              <Route path="/skills/:id" element={<SkillDetail />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="/data-overview" element={<DataOverview />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </main>
      </div>
    </ToastProvider>
  )
}

export default App
