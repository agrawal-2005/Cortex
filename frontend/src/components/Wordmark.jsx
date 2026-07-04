/**
 * Cortex wordmark — lowercase "cortex", Inter 500, tight tracking,
 * final "x" in brand purple. Never "Cortex" or "CORTEX" in lockups.
 */
export default function Wordmark({ size = 24, className = '' }) {
  return (
    <span
      className={`font-medium text-text ${className}`}
      style={{ fontSize: size, letterSpacing: '-1.5px', lineHeight: 1 }}
    >
      corte<span className="text-primary">x</span>
    </span>
  )
}
