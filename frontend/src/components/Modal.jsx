import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function Modal({ open, onClose, title, subtitle, children, wide = false }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-[3px]"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={`glass rounded-card shadow-2xl shadow-black/50 w-full ${wide ? 'max-w-2xl' : 'max-w-md'} page-enter`}>
        <div className="flex items-start justify-between px-6 pt-5 pb-3">
          <div>
            <h2 className="text-base font-semibold text-text">{title}</h2>
            {subtitle && <p className="text-sm text-text-dim mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="text-text-dim hover:text-text transition-colors mt-0.5"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-6 pb-6">{children}</div>
      </div>
    </div>
  )
}
