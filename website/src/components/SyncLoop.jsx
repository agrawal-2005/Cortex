import { motion } from 'framer-motion'
import Reveal from './Reveal'

/*
 * The auto-sync loop:
 * [New Slack message] → [Cortex detects it] → [Skill updated]
 *                          ↑                       ↓
 *                     [Continuously] ← [Confidence recalculated]
 */

const PILLS = [
  { x: 20, y: 30, w: 170, label: 'New Slack message' },
  { x: 310, y: 30, w: 160, label: 'Cortex detects it', highlight: true },
  { x: 610, y: 30, w: 150, label: 'Skill updated' },
  { x: 575, y: 150, w: 220, label: 'Confidence recalculated' },
  { x: 310, y: 150, w: 160, label: 'Continuously' },
]

const ARROWS = [
  'M 190 48 H 302', // slack msg → detects
  'M 470 48 H 602', // detects → skill updated
  'M 685 66 V 142', // skill updated ↓ confidence
  'M 567 168 H 478', // confidence ← continuously
  'M 390 142 V 74', // continuously ↑ detects
]

// Invisible track for the circulating pulse (rendered under the pills).
const LOOP_PATH = 'M 390 48 H 685 V 168 H 390 Z'

export default function SyncLoop() {
  return (
    <section className="py-24">
      <div className="max-w-4xl mx-auto px-6">
        <Reveal>
          <p className="text-xs font-medium text-primary uppercase tracking-widest text-center">
            Auto-sync
          </p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            Your brain updates itself
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="mt-12 overflow-x-auto">
            <svg viewBox="0 0 800 240" className="w-full min-w-[560px]" aria-hidden>
              <defs>
                <marker
                  id="syncloop-arrow"
                  viewBox="0 0 8 8"
                  refX="7"
                  refY="4"
                  markerWidth="7"
                  markerHeight="7"
                  orient="auto-start-reverse"
                >
                  <path d="M0 0L8 4L0 8z" fill="#6C5CE7" opacity="0.7" />
                </marker>
              </defs>

              {/* circulating pulse, slides beneath the pills */}
              <circle r="3" fill="#00D2FF" opacity="0.8">
                <animateMotion dur="7s" repeatCount="indefinite" path={LOOP_PATH} />
              </circle>

              {ARROWS.map((d, i) => (
                <motion.path
                  key={d}
                  d={d}
                  fill="none"
                  stroke="#6C5CE7"
                  strokeWidth="1.25"
                  markerEnd="url(#syncloop-arrow)"
                  initial={{ pathLength: 0, opacity: 0 }}
                  whileInView={{ pathLength: 1, opacity: 0.55 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.5, delay: 0.2 + i * 0.15, ease: 'easeOut' }}
                />
              ))}

              {PILLS.map((p, i) => (
                <motion.g
                  key={p.label}
                  initial={{ opacity: 0, y: 8 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-60px' }}
                  transition={{ duration: 0.4, delay: i * 0.12 }}
                >
                  <rect
                    x={p.x}
                    y={p.y}
                    width={p.w}
                    height="36"
                    rx="10"
                    fill="#0E0E16"
                    stroke={p.highlight ? '#6C5CE7' : '#1A1A28'}
                    strokeWidth={p.highlight ? 1.5 : 1}
                  />
                  <text
                    x={p.x + p.w / 2}
                    y={p.y + 22.5}
                    textAnchor="middle"
                    fontSize="12.5"
                    fontFamily="Inter, sans-serif"
                    fill={p.highlight ? '#E8E8ED' : '#8888A0'}
                  >
                    {p.label}
                  </text>
                </motion.g>
              ))}
            </svg>
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <p className="mt-8 text-sm text-text-dim text-center max-w-2xl mx-auto leading-relaxed">
            When your team changes a process, Cortex notices. Skills are re-extracted with
            fresh data. Confidence scores adjust automatically. No manual maintenance
            required.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
