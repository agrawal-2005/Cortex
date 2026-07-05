import Reveal from './Reveal'

/* Honest data-handling posture. Every claim here maps to a shipped
   feature - keep this section accurate when the product changes. */

function EyeIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  )
}

function TrashIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  )
}

function BoxIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5M12 22V12" />
    </svg>
  )
}

function LockIcon({ size = 18 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  )
}

const ITEMS = [
  {
    icon: EyeIcon,
    title: 'See everything',
    body: 'A dedicated transparency page lists every document Cortex has ingested: counts per source, date ranges, and sample content. What you see there is everything we have processed. Nothing beyond it is accessed.',
  },
  {
    icon: TrashIcon,
    title: 'Delete everything',
    body: 'One action hard-deletes all of it: documents, extracted skills, embeddings, and stored source tokens. Not a soft delete. Cortex re-counts every table and vector index afterward and refuses to report success unless everything is at zero.',
  },
  {
    icon: BoxIcon,
    title: 'One company at a time',
    body: 'Cortex runs single-tenant today: one deployment serves one company, with no shared multi-tenant pool. Between pilots, the workspace is verifiably wiped to zero before anyone else\u2019s data comes in.',
  },
  {
    icon: LockIcon,
    title: 'Locked down by default',
    body: 'Every API route requires a key (SHA-256 hashed, shown once). Source tokens are encrypted at rest and never returned or logged. Per-key rate limits on ingestion and queries.',
  },
]

export default function Security() {
  return (
    <section id="security" className="py-24 scroll-mt-16">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <h2 className="text-3xl sm:text-4xl font-semibold tracking-tight text-center">
            Your data, handled honestly
          </h2>
          <p className="mt-4 text-base text-text-dim text-center max-w-2xl mx-auto leading-relaxed">
            Trust features are built in, not promised. Everything below ships
            in the product today.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {ITEMS.map((item, i) => (
            <Reveal key={item.title} delay={i * 0.08}>
              <div className="h-full rounded-xl border border-border bg-surface p-6 hover:border-primary/40 transition-colors">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-bg text-secondary">
                  <item.icon />
                </div>
                <h3 className="mt-4 text-base font-semibold text-text">{item.title}</h3>
                <p className="mt-2 text-sm text-text-dim leading-relaxed">{item.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
