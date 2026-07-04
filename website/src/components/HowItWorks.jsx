import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Reveal from './Reveal'
import Logo from './Logo'

const AUTO_ADVANCE_MS = 5000

/* ---------- Step 1: Connect your tools ---------- */

const SOURCES = [
  { label: 'Slack', x: 40, y: 40 },
  { label: 'GitHub', x: 40, y: 130 },
  { label: 'Discord', x: 40, y: 220 },
  { label: 'Jira', x: 40, y: 310 },
]

function ConnectVisual() {
  const cx = 340
  const cy = 175
  return (
    <svg viewBox="0 0 440 350" className="w-full h-full">
      {SOURCES.map((s, i) => (
        <g key={s.label}>
          <path
            d={`M${s.x + 52},${s.y} C ${cx - 120},${s.y} ${cx - 140},${cy} ${cx - 34},${cy}`}
            fill="none"
            stroke="#1A1A28"
            strokeWidth="1.5"
            strokeDasharray="4 5"
          />
          {/* data pulse flowing along the line */}
          <motion.circle
            r="3"
            fill="#00D2FF"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 1, 0] }}
            transition={{ duration: 2.2, repeat: Infinity, delay: i * 0.5 }}
          >
            <animateMotion
              dur="2.2s"
              repeatCount="indefinite"
              begin={`${i * 0.5}s`}
              path={`M${s.x + 52},${s.y} C ${cx - 120},${s.y} ${cx - 140},${cy} ${cx - 34},${cy}`}
            />
          </motion.circle>
          <motion.g
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.12, duration: 0.5 }}
          >
            <rect x={s.x - 32} y={s.y - 18} width="84" height="36" rx="9" fill="#0E0E16" stroke="#1A1A28" />
            <text x={s.x + 10} y={s.y + 4} textAnchor="middle" fill="#E8E8ED" fontSize="12" fontFamily="Inter, sans-serif">
              {s.label}
            </text>
          </motion.g>
        </g>
      ))}

      {/* central Cortex node */}
      <motion.g
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        style={{ transformOrigin: `${cx}px ${cy}px` }}
      >
        <circle cx={cx} cy={cy} r="52" fill="#0E0E16" stroke="#6C5CE7" strokeWidth="1.5" />
        <motion.circle
          cx={cx}
          cy={cy}
          r="52"
          fill="none"
          stroke="#6C5CE7"
          strokeWidth="1"
          animate={{ r: [52, 64], opacity: [0.5, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
        />
        <text x={cx} y={cy + 5} textAnchor="middle" fontSize="15" fontWeight="500" letterSpacing="-0.75" fontFamily="Inter, sans-serif">
          <tspan fill="#E8E8ED">corte</tspan>
          <tspan fill="#6C5CE7">x</tspan>
        </text>
      </motion.g>
    </svg>
  )
}

/* ---------- Step 2: Knowledge is extracted ---------- */

const MESSAGES = [
  { w: 120, cluster: 0 },
  { w: 96, cluster: 1 },
  { w: 132, cluster: 0 },
  { w: 88, cluster: 2 },
  { w: 110, cluster: 1 },
  { w: 100, cluster: 2 },
  { w: 124, cluster: 0 },
  { w: 92, cluster: 1 },
  { w: 104, cluster: 2 },
]

const CLUSTER_COLORS = ['#6C5CE7', '#00D2FF', '#8888A0']

function ExtractVisual() {
  return (
    <div className="w-full h-full flex items-center justify-center gap-10 px-8">
      {/* raw messages */}
      <div className="flex flex-col gap-2.5">
        {MESSAGES.map((m, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.06, duration: 0.4 }}
            className="h-3 rounded-full bg-border"
            style={{ width: m.w }}
          />
        ))}
      </div>

      <motion.svg
        width="40"
        height="16"
        viewBox="0 0 40 16"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7 }}
      >
        <path d="M2 8h30M26 2l8 6-8 6" stroke="#6C5CE7" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </motion.svg>

      {/* clustered groups */}
      <div className="flex flex-col gap-4">
        {[0, 1, 2].map((c) => (
          <motion.div
            key={c}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.8 + c * 0.18, duration: 0.45 }}
            className="rounded-xl border p-3 flex flex-col gap-2"
            style={{ borderColor: `${CLUSTER_COLORS[c]}55`, background: '#0E0E16' }}
          >
            {MESSAGES.filter((m) => m.cluster === c).map((m, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 1 + c * 0.18 + i * 0.08, duration: 0.35 }}
                className="h-2.5 rounded-full"
                style={{ width: m.w * 0.7, background: `${CLUSTER_COLORS[c]}99` }}
              />
            ))}
          </motion.div>
        ))}
      </div>
    </div>
  )
}

/* ---------- Step 3: Skills are structured ---------- */

const SKILL_STEPS = [
  { text: 'Create tenant in provisioning system', conf: 0.88 },
  { text: 'Configure SSO with client identity provider', conf: 0.74 },
  { text: 'Run smoke tests against staging', conf: 0.81 },
]

function StructureVisual() {
  return (
    <div className="w-full h-full flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md bg-surface border border-border rounded-xl p-5"
      >
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold">Client Onboarding</h4>
          <span className="text-[10px] font-medium text-primary bg-primary/10 border border-primary/25 rounded-full px-2.5 py-1">
            confidence 0.82
          </span>
        </div>
        <div className="mt-4 space-y-3">
          {SKILL_STEPS.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -14 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.2, duration: 0.4 }}
              className="bg-bg border border-border rounded-lg px-3.5 py-2.5"
            >
              <div className="flex items-center gap-2.5">
                <span className="w-5 h-5 rounded-md bg-primary/15 text-primary text-[10px] font-semibold flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <p className="text-xs flex-1">{s.text}</p>
              </div>
              <div className="mt-2 flex items-center gap-2 pl-7.5">
                <div className="h-1 flex-1 rounded-full bg-border overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-secondary/70"
                    initial={{ width: 0 }}
                    animate={{ width: `${s.conf * 100}%` }}
                    transition={{ delay: 0.6 + i * 0.2, duration: 0.5 }}
                  />
                </div>
                <span className="text-[10px] text-text-dim tabular-nums">{Math.round(s.conf * 100)}%</span>
                <span className="text-[10px] text-secondary">3 sources ↗</span>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  )
}

/* ---------- Step 4: Agents execute ---------- */

const JSON_LINES = [
  [{ t: '{', c: 'text' }],
  [{ t: '  "skill"', c: 'key' }, { t: ': ', c: 'text' }, { t: '"client_onboarding"', c: 'str' }, { t: ',', c: 'text' }],
  [{ t: '  "confidence"', c: 'key' }, { t: ': ', c: 'text' }, { t: '0.82', c: 'num' }, { t: ',', c: 'text' }],
  [{ t: '  "steps"', c: 'key' }, { t: ': [{', c: 'text' }],
  [{ t: '    "action"', c: 'key' }, { t: ': ', c: 'text' }, { t: '"Create tenant"', c: 'str' }, { t: ',', c: 'text' }],
  [{ t: '    "tool"', c: 'key' }, { t: ': ', c: 'text' }, { t: '"POST /tenants"', c: 'str' }, { t: ',', c: 'text' }],
  [{ t: '    "on_failure"', c: 'key' }, { t: ': ', c: 'text' }, { t: '"escalate"', c: 'str' }],
  [{ t: '  }]', c: 'text' }],
  [{ t: '}', c: 'text' }],
]

const TOKEN_COLORS = { key: '#00D2FF', str: '#6C5CE7', num: '#E8E8ED', text: '#8888A0' }

function ExecuteVisual() {
  return (
    <div className="w-full h-full flex flex-col sm:flex-row items-stretch justify-center gap-4 px-6 py-4">
      <motion.div
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="flex-1 max-w-xs bg-bg border border-border rounded-xl overflow-hidden"
      >
        <div className="px-4 py-2 border-b border-border text-[10px] font-medium text-secondary uppercase tracking-wider">
          For AI agents
        </div>
        <pre className="p-4 text-[11px] leading-relaxed font-mono overflow-hidden">
          {JSON_LINES.map((line, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              {line.map((tok, j) => (
                <span key={j} style={{ color: TOKEN_COLORS[tok.c] }}>{tok.t}</span>
              ))}
            </motion.div>
          ))}
        </pre>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="flex-1 max-w-xs bg-surface border border-border rounded-xl overflow-hidden"
      >
        <div className="px-4 py-2 border-b border-border text-[10px] font-medium text-primary uppercase tracking-wider">
          For humans
        </div>
        <div className="p-4 text-xs leading-relaxed text-text-dim space-y-2.5">
          {[
            'Client Onboarding (82% confidence)',
            '1. Create the tenant by calling POST /tenants.',
            '2. If it fails, escalate to the pre-sales lead.',
            'Sources: 3 Slack threads, 1 GitHub PR.',
          ].map((line, i) => (
            <motion.p
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 + i * 0.15 }}
              className={i === 0 ? 'text-text font-medium' : ''}
            >
              {line}
            </motion.p>
          ))}
        </div>
      </motion.div>
    </div>
  )
}

/* ---------- Stepper ---------- */

function SyncIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      width={14}
      height={14}
      fill="none"
      className="shrink-0 mt-0.5 animate-[spin_8s_linear_infinite]"
      aria-hidden
    >
      <path d="M20 12a8 8 0 11-2.34-5.66" stroke="#6C5CE7" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M20 3v4h-4" stroke="#00D2FF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const STEPS = [
  {
    title: 'Connect your tools',
    text: 'Connect Slack, GitHub, Discord, or upload files. Cortex reads public channels, PRs, issues, and docs.',
    note: 'Connect once. Cortex syncs automatically — new messages, PRs, and tickets flow in continuously. Your knowledge never goes stale.',
    Visual: ConnectVisual,
  },
  {
    title: 'Knowledge is extracted',
    text: 'AI reads thousands of messages and automatically discovers the workflows hidden in your conversations.',
    Visual: ExtractVisual,
  },
  {
    title: 'Skills are structured',
    text: 'Each workflow becomes a structured skill — with steps, tools, edge cases, and links back to every source.',
    Visual: StructureVisual,
  },
  {
    title: 'Agents execute',
    text: 'AI agents get executable JSON. Humans get plain English. Same knowledge, two formats.',
    Visual: ExecuteVisual,
  },
]

export default function HowItWorks() {
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    if (paused) return
    const id = setInterval(() => {
      setActive((a) => (a + 1) % STEPS.length)
    }, AUTO_ADVANCE_MS)
    return () => clearInterval(id)
  }, [paused])

  const Visual = STEPS[active].Visual

  return (
    <section id="how-it-works" className="py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <p className="text-xs font-medium text-primary uppercase tracking-widest text-center">
            How it works
          </p>
          <h2 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            From scattered chatter to executable skills
          </h2>
        </Reveal>

        <Reveal delay={0.15}>
          <div
            className="mt-14 grid lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-8 items-stretch"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            {/* Step navigation */}
            <div className="flex flex-col gap-2.5">
              {STEPS.map((step, i) => {
                const isActive = i === active
                return (
                  <button
                    key={step.title}
                    onClick={() => setActive(i)}
                    className={`relative text-left rounded-xl border px-5 py-4 transition-colors overflow-hidden ${
                      isActive
                        ? 'bg-surface border-primary/40'
                        : 'bg-transparent border-border hover:border-primary/20'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={`w-6 h-6 rounded-full text-[11px] font-semibold flex items-center justify-center shrink-0 ${
                          isActive ? 'bg-primary text-white' : 'bg-surface border border-border text-text-dim'
                        }`}
                      >
                        {i + 1}
                      </span>
                      <h3 className={`text-sm font-semibold ${isActive ? 'text-text' : 'text-text-dim'}`}>
                        {step.title}
                      </h3>
                    </div>
                    <AnimatePresence initial={false}>
                      {isActive && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.3 }}
                          className="pl-9 overflow-hidden"
                        >
                          <p className="text-sm text-text-dim leading-relaxed pt-2">{step.text}</p>
                          {step.note && (
                            <p className="mt-2 flex items-start gap-2 text-sm text-text-dim leading-relaxed">
                              <SyncIcon />
                              <span>{step.note}</span>
                            </p>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                    {/* progress indicator */}
                    {isActive && (
                      <motion.div
                        key={`progress-${active}-${paused}`}
                        className="absolute bottom-0 left-0 h-0.5 bg-primary/60"
                        initial={{ width: '0%' }}
                        animate={{ width: paused ? '0%' : '100%' }}
                        transition={{ duration: AUTO_ADVANCE_MS / 1000, ease: 'linear' }}
                      />
                    )}
                  </button>
                )
              })}
            </div>

            {/* Visual */}
            <div className="relative min-h-[24rem] bg-surface/50 border border-border rounded-2xl overflow-hidden">
              <div
                aria-hidden
                className="absolute inset-0 pointer-events-none"
                style={{
                  background:
                    'radial-gradient(ellipse 70% 60% at 50% 50%, rgba(108,92,231,0.06), transparent 70%)',
                }}
              />
              <AnimatePresence mode="wait">
                <motion.div
                  key={active}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.35 }}
                  className="absolute inset-0"
                >
                  <Visual />
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
