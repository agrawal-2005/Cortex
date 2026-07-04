// Shared UI helpers: status/department/confidence color maps and formatters.

export const STATUS_STYLES = {
  verified: { label: 'Verified', className: 'bg-success/15 text-success border-success/30' },
  review: { label: 'In Review', className: 'bg-warning/15 text-warning border-warning/30' },
  draft: { label: 'Draft', className: 'bg-text-dim/15 text-text-dim border-text-dim/30' },
  outdated: { label: 'Outdated', className: 'bg-danger/15 text-danger border-danger/30' },
}

export const DEPT_STYLES = {
  engineering: 'bg-primary/15 text-primary border-primary/30',
  support: 'bg-secondary/15 text-secondary border-secondary/30',
  sales: 'bg-success/15 text-success border-success/30',
  marketing: 'bg-[#ff79c6]/15 text-[#ff79c6] border-[#ff79c6]/30',
  operations: 'bg-warning/15 text-warning border-warning/30',
  general: 'bg-text-dim/15 text-text-dim border-text-dim/30',
}

export function deptStyle(department) {
  const key = (department || 'general').toLowerCase()
  return DEPT_STYLES[key] || DEPT_STYLES.general
}

export function confidenceColor(value) {
  // value in [0, 1]
  if (value >= 0.75) return 'var(--color-success)'
  if (value >= 0.5) return 'var(--color-warning)'
  return 'var(--color-danger)'
}

export function pct(value) {
  return `${Math.round((value || 0) * 100)}%`
}

export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

// Map Document.source_type values to integration keys (single source of
// truth — used by both the Dashboard stat and the Data Sources page so the
// two never disagree about what is "connected"). Generic rule: the key is
// the prefix before the first "_" (github_pr → github), so any newly
// ingested source type shows up without code changes. Aliases cover
// source types whose integration key differs from their prefix.
const SOURCE_KEY_ALIASES = { custom_api: 'api', custom: 'file' }

export function sourceKeyOf(sourceType) {
  if (!sourceType) return null
  return SOURCE_KEY_ALIASES[sourceType] || sourceType.split('_')[0]
}

export function timeAgo(value) {
  if (!value) return '—'
  const d = new Date(value)
  const seconds = Math.floor((Date.now() - d.getTime()) / 1000)
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return formatDate(value)
}
