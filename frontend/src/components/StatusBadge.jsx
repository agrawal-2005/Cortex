const STATUS_STYLES = {
  draft: 'bg-gray-100 text-gray-700 ring-gray-500/20',
  review: 'bg-yellow-100 text-yellow-700 ring-yellow-600/20',
  verified: 'bg-emerald-100 text-emerald-700 ring-emerald-600/20',
  outdated: 'bg-red-100 text-red-700 ring-red-600/20',
}

function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.draft

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ring-1 ring-inset ${style}`}
    >
      {status}
    </span>
  )
}

export default StatusBadge
