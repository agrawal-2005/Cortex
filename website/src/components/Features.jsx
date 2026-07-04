import Reveal from './Reveal'

const stroke = { fill: 'none', strokeWidth: 1.5, strokeLinecap: 'round', strokeLinejoin: 'round' }

const FEATURES = [
  {
    title: 'Multi-source ingestion',
    body: 'Slack, GitHub, Discord, Jira, file uploads. One brain, every source.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M12 3v6M5 15l4-3M19 15l-4-3" stroke="#00D2FF" {...stroke} />
        <circle cx="12" cy="12" r="2.5" stroke="#6C5CE7" {...stroke} />
        <circle cx="12" cy="3" r="1.5" fill="#6C5CE7" />
        <circle cx="5" cy="15" r="1.5" fill="#6C5CE7" opacity="0.6" />
        <circle cx="19" cy="15" r="1.5" fill="#6C5CE7" opacity="0.6" />
      </svg>
    ),
  },
  {
    title: 'Source tracing',
    body: 'Every claim links back to the exact Slack message or GitHub PR it came from.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M10 14a4 4 0 005.6.4l3-3a4 4 0 00-5.6-5.6l-1.5 1.5" stroke="#6C5CE7" {...stroke} />
        <path d="M14 10a4 4 0 00-5.6-.4l-3 3a4 4 0 005.6 5.6l1.5-1.5" stroke="#00D2FF" {...stroke} />
      </svg>
    ),
  },
  {
    title: 'Feedback loop',
    body: 'Reject a wrong step. Cortex learns. Next extraction gets it right.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M4 12a8 8 0 0114-5M20 12a8 8 0 01-14 5" stroke="#6C5CE7" {...stroke} />
        <path d="M18 3v4h-4M6 21v-4h4" stroke="#00D2FF" {...stroke} />
      </svg>
    ),
  },
  {
    title: 'Agent-ready API',
    body: 'Structured JSON that AI agents execute directly. No prompt engineering needed.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M8 7l-4 5 4 5M16 7l4 5-4 5" stroke="#6C5CE7" {...stroke} />
        <path d="M13 5l-2 14" stroke="#00D2FF" {...stroke} />
      </svg>
    ),
  },
  {
    title: 'Security built in',
    body: 'API key auth, token encryption, rate limiting. Your data stays your data.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z" stroke="#6C5CE7" {...stroke} />
        <path d="M9 12l2 2 4-4" stroke="#00D2FF" {...stroke} />
      </svg>
    ),
  },
  {
    title: 'Confidence scoring',
    body: 'Every skill shows how confident the extraction is. Review what needs attention.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22}>
        <path d="M4 19h16" stroke="#8888A0" {...stroke} />
        <path d="M6 19v-5M11 19V8M16 19v-8M21 19V5" stroke="#6C5CE7" {...stroke} />
        <circle cx="21" cy="5" r="1.5" fill="#00D2FF" />
      </svg>
    ),
  },
  {
    title: 'Always in sync',
    body: 'Cortex watches your tools continuously. New conversations and tickets are ingested automatically. Your company brain stays current.',
    icon: (
      <svg viewBox="0 0 24 24" width={22} height={22} className="animate-[spin_10s_linear_infinite]">
        <path d="M20 12a8 8 0 11-2.34-5.66" stroke="#6C5CE7" {...stroke} />
        <path d="M20 3v4h-4" stroke="#00D2FF" {...stroke} />
        <circle cx="12" cy="12" r="2" fill="#00D2FF" />
      </svg>
    ),
  },
]

export default function Features() {
  return (
    <section id="features" className="py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center max-w-xl mx-auto">
            Built for companies moving to AI automation
          </h2>
        </Reveal>

        <div className="mt-14 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={(i % 3) * 0.08}>
              <div className="group h-full bg-surface border border-border rounded-xl p-6 transition-all duration-300 hover:border-primary/40 hover:shadow-[0_0_24px_rgba(108,92,231,0.12)]">
                <span className="inline-flex w-10 h-10 rounded-lg bg-bg border border-border items-center justify-center">
                  {f.icon}
                </span>
                <h3 className="mt-4 text-sm font-semibold">{f.title}</h3>
                <p className="mt-1.5 text-sm text-text-dim leading-relaxed">{f.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
