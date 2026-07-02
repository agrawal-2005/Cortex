function ConfidenceBadge({ score }) {
  const pct = Math.round((score ?? 0) * 100)

  let colorClasses
  if (score > 0.7) {
    colorClasses = 'bg-green-100 text-green-800 ring-green-600/20'
  } else if (score > 0.4) {
    colorClasses = 'bg-yellow-100 text-yellow-800 ring-yellow-600/20'
  } else {
    colorClasses = 'bg-red-100 text-red-800 ring-red-600/20'
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${colorClasses}`}
    >
      {pct}%
    </span>
  )
}

export default ConfidenceBadge
