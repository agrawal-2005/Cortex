import { useEffect, useState } from 'react'
import Logo from './Logo'
import Wordmark from './Wordmark'

// Product dashboard (separate Vite app in ../frontend). Overridable per env.
const APP_URL = import.meta.env.VITE_APP_URL || 'http://localhost:3000'

const LINKS = [
  { href: '#how-it-works', label: 'How It Works' },
  { href: '#features', label: 'Features' },
  { href: '#demo', label: 'Demo' },
  { href: '#security', label: 'Security' },
  { href: '#pricing', label: 'Pricing' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      className={`fixed top-0 inset-x-0 z-50 transition-colors duration-300 ${
        scrolled
          ? 'bg-bg/85 backdrop-blur-md border-b border-border'
          : 'bg-transparent border-b border-transparent'
      }`}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2.5">
          <Logo size={30} />
          <Wordmark size={24} />
        </a>

        <div className="hidden md:flex items-center gap-8">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="text-sm text-text-dim hover:text-text transition-colors"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <a
            href={APP_URL}
            className="hidden sm:inline text-sm text-text-dim hover:text-text transition-colors"
          >
            Open App
          </a>
          <a
            href="#cta"
            className="text-sm font-medium bg-primary hover:bg-primary/85 text-white rounded-lg px-4 py-2 transition-colors"
          >
            Get Early Access
          </a>
        </div>
      </div>
    </nav>
  )
}
