import { STATUS_STYLES, deptStyle, confidenceColor, pct } from '../lib/ui'

// ── Badges ────────────────────────────────────────────────────────────

export function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.draft
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border whitespace-nowrap shrink-0 ${s.className}`}>
      {s.label}
    </span>
  )
}

export function DeptBadge({ department }) {
  if (!department) return null
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border capitalize whitespace-nowrap shrink-0 ${deptStyle(department)}`}>
      {department}
    </span>
  )
}

export function ToolBadge({ children }) {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono bg-bg border border-border text-text-dim">
      {children}
    </span>
  )
}

// ── Confidence bar ────────────────────────────────────────────────────

export function ConfidenceBar({ value, showLabel = true, className = '' }) {
  const color = confidenceColor(value)
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-1.5 flex-1 rounded-full bg-border overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: pct(value), backgroundColor: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium tabular-nums" style={{ color }}>
          {pct(value)}
        </span>
      )}
    </div>
  )
}

// ── Skeletons ─────────────────────────────────────────────────────────

export function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} />
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="card p-5 space-y-3">
      <Skeleton className="h-4 w-2/3" />
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className="h-3 w-full" />
      ))}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────

export function EmptyState({ icon: Icon, title, message, action }) {
  return (
    <div className="card flex flex-col items-center justify-center text-center py-14 px-6">
      {Icon && (
        <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-4">
          <Icon size={26} className="text-primary" />
        </div>
      )}
      <h3 className="text-base font-semibold text-text">{title}</h3>
      {message && <p className="text-sm text-text-dim mt-1.5 max-w-sm">{message}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

// ── Buttons ───────────────────────────────────────────────────────────

export function Button({ variant = 'default', className = '', children, ...props }) {
  const variants = {
    primary: 'gradient-brand text-white hover:opacity-90 disabled:opacity-50',
    default: 'bg-surface-2 border border-border text-text hover:border-primary/50 disabled:opacity-50',
    success: 'bg-success/15 border border-success/30 text-success hover:bg-success/25 disabled:opacity-50',
    warning: 'bg-warning/15 border border-warning/30 text-warning hover:bg-warning/25 disabled:opacity-50',
    danger: 'bg-danger/15 border border-danger/30 text-danger hover:bg-danger/25 disabled:opacity-50',
    ghost: 'text-text-dim hover:text-text hover:bg-surface-2 disabled:opacity-50',
  }
  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
