import { motion } from 'framer-motion'
import Reveal from './Reveal'
import { siGithub, siDiscord, siJira, siNotion, siConfluence, siLinear } from 'simple-icons'

function BrandIcon({ path, color, size = 26 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={color} aria-hidden>
      <path d={path} />
    </svg>
  )
}

/* Official Slack mark - removed from simple-icons, inlined with its four brand colors. */
function SlackIcon({ size = 26 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden>
      <path
        fill="#E01E5A"
        d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z"
      />
      <path
        fill="#36C5F0"
        d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z"
      />
      <path
        fill="#2EB67D"
        d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z"
      />
      <path
        fill="#ECB22E"
        d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"
      />
    </svg>
  )
}

/* Official multicolor Gmail envelope. */
function GmailIcon({ size = 26 }) {
  return (
    <svg viewBox="52 42 88 66" width={size} height={size} aria-hidden>
      <path fill="#4285F4" d="M58 108h14V74L52 59v43c0 3.32 2.69 6 6 6" />
      <path fill="#34A853" d="M120 108h14c3.32 0 6-2.69 6-6V59l-20 15" />
      <path fill="#FBBC04" d="M120 48v26l20-15v-8c0-7.42-8.47-11.65-14.4-7.2" />
      <path fill="#EA4335" d="M72 74V48l24 18 24-18v26L96 92" />
      <path fill="#C5221F" d="M52 59v8l20 15V48l-5.6-4.2c-5.94-4.45-14.4-.22-14.4 7.2" />
    </svg>
  )
}

/* Microsoft Teams isn't in simple-icons - flat rendition of the official mark. */
function TeamsIcon({ size = 26 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden>
      <circle cx="19.1" cy="6.6" r="2.3" fill="#5059C9" />
      <path
        d="M16.2 10.2h6.6c.66 0 1.2.54 1.2 1.2v4.2a4.1 4.1 0 0 1-4.1 4.1 4.1 4.1 0 0 1-3.7-2.35z"
        fill="#5059C9"
      />
      <circle cx="13.3" cy="5.2" r="3.1" fill="#7B83EB" />
      <path
        d="M8.9 9.5h8.8c.66 0 1.2.54 1.2 1.2v5.6a5.3 5.3 0 0 1-5.3 5.3 5.3 5.3 0 0 1-5.3-5.3v-6.2c0-.33.27-.6.6-.6z"
        fill="#7B83EB"
      />
      <rect x="0.8" y="6.6" width="11.6" height="11.6" rx="1.5" fill="#4B53BC" />
      <path d="M4 10.2h5.2M6.6 10.2v5.4" stroke="#fff" strokeWidth="1.7" strokeLinecap="round" fill="none" />
    </svg>
  )
}

function PlusIcon({ size = 26 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden>
      <path d="M12 4v16M4 12h16" stroke="#6C5CE7" strokeWidth="2.2" strokeLinecap="round" fill="none" />
    </svg>
  )
}

/* Brand hexes that vanish on a near-black page get a light or brighter fill. */
const PLATFORMS = [
  { label: 'Slack', icon: <SlackIcon /> },
  { label: 'GitHub', icon: <BrandIcon path={siGithub.path} color="#E8E8ED" /> },
  { label: 'Discord', icon: <BrandIcon path={siDiscord.path} color="#5865F2" /> },
  { label: 'Jira', icon: <BrandIcon path={siJira.path} color="#2684FF" /> },
  { label: 'Notion', icon: <BrandIcon path={siNotion.path} color="#E8E8ED" /> },
  { label: 'Gmail', icon: <GmailIcon /> },
  { label: 'Confluence', icon: <BrandIcon path={siConfluence.path} color="#2684FF" /> },
  { label: 'Linear', icon: <BrandIcon path={siLinear.path} color="#5E6AD2" /> },
  { label: 'Teams', icon: <TeamsIcon /> },
  { label: 'Any API', icon: <PlusIcon />, dashed: true },
]

/* Converging data-flow lines: 10 sources → one cortex dot. */
function ConvergenceVisual() {
  const cx = 500
  const dotY = 112
  const paths = PLATFORMS.map((_, i) => {
    const x = 50 + i * 100
    return `M ${x} 0 C ${x} 55, ${cx} 55, ${cx} ${dotY - 10}`
  })

  return (
    <svg viewBox="0 0 1000 170" className="w-full mt-1" aria-hidden>
      {paths.map((d, i) => (
        <g key={d}>
          <motion.path
            d={d}
            fill="none"
            stroke="#6C5CE7"
            strokeWidth="1"
            initial={{ pathLength: 0, opacity: 0 }}
            whileInView={{ pathLength: 1, opacity: 0.22 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.9, delay: i * 0.06, ease: 'easeOut' }}
          />
          {i % 3 === 0 && (
            <motion.circle
              r="2"
              fill="#00D2FF"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: [0, 0.7, 0] }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 2.4, delay: 1 + i * 0.15, repeat: Infinity, repeatDelay: 1.2 }}
            >
              <animateMotion dur="3.6s" repeatCount="indefinite" path={d} />
            </motion.circle>
          )}
        </g>
      ))}

      {/* the brain */}
      <circle cx={cx} cy={dotY} r="9" fill="#6C5CE7" opacity="0.12" />
      <circle cx={cx} cy={dotY} r="4" fill="#6C5CE7" />
      <motion.circle
        cx={cx}
        cy={dotY}
        fill="none"
        stroke="#6C5CE7"
        strokeWidth="1"
        animate={{ r: [5, 14], opacity: [0.5, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
      />
      <text
        x={cx}
        y={dotY + 34}
        textAnchor="middle"
        fontSize="17"
        fontWeight="500"
        letterSpacing="-1"
        fontFamily="Inter, sans-serif"
      >
        <tspan fill="#E8E8ED">corte</tspan>
        <tspan fill="#6C5CE7">x</tspan>
      </text>
    </svg>
  )
}

export default function Integrations() {
  return (
    <section id="integrations" className="py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            Works with the tools you already use
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-12 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {PLATFORMS.map((p, i) => (
              <motion.div
                key={p.label}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.4, delay: i * 0.04 }}
                whileHover={{ y: -4 }}
                className={`flex flex-col items-center justify-center gap-3 rounded-xl bg-surface px-4 py-7 transition-colors ${
                  p.dashed
                    ? 'border border-dashed border-primary/40 hover:border-primary/70'
                    : 'border border-border hover:border-primary/40 hover:shadow-[0_0_24px_rgba(108,92,231,0.12)]'
                }`}
              >
                {p.icon}
                <span className="text-sm text-text-dim">{p.label}</span>
              </motion.div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <p className="mt-6 text-sm text-text-dim text-center">
            Connect any tool with an API. Upload CSV, JSON, or PDF for everything else.
          </p>
        </Reveal>

        <div className="hidden sm:block">
          <ConvergenceVisual />
        </div>

        <Reveal delay={0.1}>
          <p className="mt-8 sm:mt-2 text-sm text-text-dim text-center">
            Don't see your tool? Cortex connects to almost anything, no custom setup
            needed.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
