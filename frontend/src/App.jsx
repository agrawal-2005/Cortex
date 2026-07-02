import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import SkillDetail from './pages/SkillDetail'
import ReviewQueue from './pages/ReviewQueue'
import IngestPage from './pages/IngestPage'
import QueryPage from './pages/QueryPage'
import DocumentsList from './pages/DocumentsList'

function NavItem({ to, children, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? 'bg-indigo-700 text-white'
            : 'text-indigo-200 hover:bg-indigo-800 hover:text-white'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-indigo-900 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <NavLink to="/" className="flex items-center space-x-2">
              <svg
                className="w-8 h-8 text-indigo-300"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5.002 5.002 0 017.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              <span className="text-xl font-bold text-white tracking-tight">
                Cortex
              </span>
            </NavLink>

            {/* Nav Links */}
            <div className="flex items-center space-x-1">
              <NavItem to="/" end>Dashboard</NavItem>
              <NavItem to="/review">Review</NavItem>
              <NavItem to="/ingest">Ingest</NavItem>
              <NavItem to="/query">Query</NavItem>
            </div>
          </div>
        </div>
      </nav>

      {/* Page Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/skills/:id" element={<SkillDetail />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/ingest" element={<IngestPage />} />
          <Route path="/query" element={<QueryPage />} />
          <Route path="/documents" element={<DocumentsList />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
