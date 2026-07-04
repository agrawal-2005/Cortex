import Reveal from './Reveal'

function ScatterIcon() {
  return (
    <svg viewBox="0 0 32 32" width={28} height={28} fill="none">
      <rect x="3" y="4" width="9" height="7" rx="2" stroke="#6C5CE7" strokeWidth="1.5" />
      <rect x="20" y="8" width="9" height="7" rx="2" stroke="#8888A0" strokeWidth="1.5" />
      <rect x="7" y="20" width="9" height="7" rx="2" stroke="#8888A0" strokeWidth="1.5" />
      <circle cx="24" cy="24" r="2" fill="#00D2FF" />
      <circle cx="17" cy="14" r="1.5" fill="#6C5CE7" opacity="0.6" />
    </svg>
  )
}

function FadedDocIcon() {
  return (
    <svg viewBox="0 0 32 32" width={28} height={28} fill="none">
      <path d="M9 4h10l5 5v19H9z" stroke="#8888A0" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M19 4v5h5" stroke="#8888A0" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M12 14h8" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M12 18h8" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
      <path d="M12 22h5" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" opacity="0.25" />
    </svg>
  )
}

function StaleClockIcon() {
  return (
    <svg viewBox="0 0 32 32" width={28} height={28} fill="none">
      <circle cx="14" cy="16" r="10" stroke="#8888A0" strokeWidth="1.5" />
      <path d="M14 10v6l4 3" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M27 7v6" stroke="#00D2FF" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="27" cy="17" r="1.2" fill="#00D2FF" />
    </svg>
  )
}

const CARDS = [
  {
    icon: ScatterIcon,
    title: 'Scattered across tools',
    body: 'Critical processes live in Slack threads, Jira tickets, GitHub PRs, and people\u2019s heads. No single source of truth.',
  },
  {
    icon: FadedDocIcon,
    title: 'Never properly documented',
    body: 'The wiki is 18 months outdated. The real process exists only as tribal knowledge passed between team members.',
  },
  {
    icon: StaleClockIcon,
    title: 'Knowledge goes stale instantly',
    body: 'Someone changed the process last week. The wiki still says the old way. Your AI agent is giving wrong answers based on outdated information.',
  },
]

export default function Problem() {
  return (
    <section className="py-24">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center max-w-2xl mx-auto">
            Your company&rsquo;s knowledge is everywhere except where AI needs it
          </h2>
        </Reveal>

        <div className="mt-14 grid md:grid-cols-3 gap-5">
          {CARDS.map((card, i) => (
            <Reveal key={card.title} delay={i * 0.1}>
              <div className="h-full bg-surface border border-border rounded-xl p-6">
                <card.icon />
                <h3 className="mt-4 text-base font-semibold">{card.title}</h3>
                <p className="mt-2 text-sm text-text-dim leading-relaxed">{card.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
