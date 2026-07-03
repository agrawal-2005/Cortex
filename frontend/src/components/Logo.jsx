/**
 * Cortex logo mark — circuit pathways converging into a center point.
 * Purple (#6C5CE7) = the brain, cyan (#00D2FF) = the connections.
 */
export default function Logo({ size = 36, className = '' }) {
  return (
    <svg
      viewBox="-1 -1 38 38"
      width={size}
      height={size}
      className={className}
      role="img"
      aria-label="Cortex"
    >
      <rect x="0" y="0" width="36" height="36" rx="8" fill="none" stroke="#6C5CE7" strokeWidth="1.5" />
      <path d="M10,10 L10,18 L18,18" fill="none" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M26,10 L26,15 L18,15 L18,18" fill="none" stroke="#00D2FF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10,26 L14,26 L14,22 L18,22 L18,18" fill="none" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.55" />
      <path d="M26,26 L22,26 L22,22 L18,22" fill="none" stroke="#00D2FF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.55" />
      <circle cx="10" cy="10" r="2" fill="#6C5CE7" />
      <circle cx="26" cy="10" r="2" fill="#00D2FF" />
      <circle cx="10" cy="26" r="2" fill="#6C5CE7" opacity="0.65" />
      <circle cx="26" cy="26" r="2" fill="#00D2FF" opacity="0.65" />
      <circle cx="18" cy="18" r="3" fill="#6C5CE7" />
    </svg>
  )
}
