import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Search, ClipboardList,
  CheckCircle2, Plug, ShieldCheck, Settings, ExternalLink,
} from 'lucide-react'
import Logo from './Logo'
import Wordmark from './Wordmark'

// Marketing site (separate Vite app in ../website). Overridable per env.
const SITE_URL = import.meta.env.VITE_SITE_URL || 'http://localhost:5173'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/query', label: 'Query', icon: Search },
  { to: '/skills', label: 'Skills', icon: ClipboardList },
  { to: '/review', label: 'Review Queue', icon: CheckCircle2 },
  { to: '/sources', label: 'Data Sources', icon: Plug },
  { to: '/data-overview', label: 'Your Data', icon: ShieldCheck },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-16 md:w-60 bg-surface border-r border-border flex flex-col">
      {/* Logo */}
      <NavLink to="/" className="flex items-center gap-3 px-3 md:px-5 h-16 border-b border-border shrink-0">
        <Logo size={36} className="shrink-0" />
        <Wordmark size={24} className="hidden md:block" />
        <span className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded-full border border-primary/30 bg-primary/10 text-primary text-[10px] font-medium tracking-wide">
          App
        </span>
      </NavLink>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 md:px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            title={label}
            className={({ isActive }) =>
              `relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors justify-center md:justify-start ${
                isActive
                  ? 'bg-primary/15 text-primary'
                  : 'text-text-dim hover:text-text hover:bg-surface-2'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-primary" />
                )}
                <Icon size={18} className="shrink-0" />
                <span className="hidden md:inline">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="hidden md:block px-5 py-4 border-t border-border space-y-2">
        <p className="text-[11px] text-text-dim leading-relaxed">
          Turn tribal knowledge into{' '}
          <span className="gradient-text font-medium">AI automation</span>
        </p>
        <a
          href={SITE_URL}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-[11px] text-text-dim hover:text-text transition-colors"
        >
          <ExternalLink size={11} />
          Website
        </a>
      </div>
    </aside>
  )
}
