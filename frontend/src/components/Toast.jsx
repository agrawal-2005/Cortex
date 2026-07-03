import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: <CheckCircle2 size={17} className="text-success shrink-0" />,
  warning: <AlertTriangle size={17} className="text-warning shrink-0" />,
  error: <XCircle size={17} className="text-danger shrink-0" />,
  info: <Info size={17} className="text-secondary shrink-0" />,
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback((message, type = 'success', duration = 4000) => {
    const id = ++idRef.current
    setToasts((prev) => [...prev, { id, message, type }])
    if (duration) setTimeout(() => dismiss(id), duration)
  }, [dismiss])

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-80">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="toast-enter glass rounded-card px-4 py-3 flex items-start gap-3 shadow-xl shadow-black/40"
          >
            {ICONS[t.type] || ICONS.info}
            <p className="text-sm text-text flex-1">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="text-text-dim hover:text-text transition-colors"
              aria-label="Dismiss"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const toast = useContext(ToastContext)
  if (!toast) throw new Error('useToast must be used within ToastProvider')
  return toast
}
