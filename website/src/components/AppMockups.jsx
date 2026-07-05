import { siGithub, siJira, siConfluence, siDiscord } from 'simple-icons'
import { SlackMini, DocIcon } from './SkillShowcase'

/*
 * Static mockups of the product pages for the demo section - rendered from
 * frozen data (no screenshots, no API) so they always match the brand theme.
 */

/* ---------- shared bits ---------- */

export function TrafficLights() {
  return (
    <>
      <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F57]" />
      <span className="h-2.5 w-2.5 rounded-full bg-[#FEBC2E]" />
      <span className="h-2.5 w-2.5 rounded-full bg-[#28C840]" />
    </>
  )
}

export function Frame({ title, className = '', children }) {
  return (
    <div className={`overflow-hidden rounded-xl border border-border bg-surface ${className}`}>
      <div className="flex items-center gap-1.5 border-b border-border px-4 py-2.5">
        <TrafficLights />
        <span className="ml-3 text-[11px] text-text-dim">{title}</span>
      </div>
      <div className="bg-bg/60 p-5 sm:p-6">{children}</div>
    </div>
  )
}

function confColor(c) {
  if (c < 0.6) return 'bg-red-400'
  if (c < 0.75) return 'bg-amber-400'
  return 'bg-emerald-400'
}

function ConfBar({ value, width = 'w-24' }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`${width} h-1.5 rounded-full bg-border overflow-hidden`}>
        <div
          className={`h-full rounded-full ${confColor(value)}`}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className="text-[10px] font-medium tabular-nums text-text-dim">
        {Math.round(value * 100)}%
      </span>
    </div>
  )
}

function DeptChip({ children }) {
  return (
    <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-text-dim">
      {children}
    </span>
  )
}

function BrandIcon({ path, color, size = 16 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill={color} aria-hidden>
      <path d={path} />
    </svg>
  )
}

/* ---------- Dashboard ---------- */

function ClipboardIcon({ size = 13 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect width="8" height="4" x="8" y="2" rx="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="M12 11h4M8 11h.01M12 16h4M8 16h.01" />
    </svg>
  )
}

function PlugIcon({ size = 13 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 22v-5M9 8V2M15 8V2M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z" />
    </svg>
  )
}

function GaugeIcon({ size = 13 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="m12 14 4-4" />
      <path d="M3.34 19a10 10 0 1 1 17.32 0" />
    </svg>
  )
}

function StatCard({ label, icon, value, valueClass = 'text-text', children }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-3.5">
      <div className="flex items-center justify-between">
        <p className="text-[9px] font-medium uppercase tracking-wider text-text-dim">{label}</p>
        {icon}
      </div>
      <p className={`mt-1.5 text-xl font-bold tabular-nums ${valueClass}`}>{value}</p>
      <div className="mt-0.5 text-[10px] text-text-dim">{children}</div>
    </div>
  )
}

const DEPTS = [
  { name: 'engineering', count: 11, color: '#6C5CE7' },
  { name: 'support', count: 8, color: '#00D2FF' },
  { name: 'sales', count: 5, color: '#00E676' },
  { name: 'hr', count: 4, color: '#FFB300' },
]

const ACTIVITY = [
  { text: 'Skill extracted: Deploy to Staging with Smoke Tests and Canary', time: '2m ago', accent: true },
  { text: 'Ingested from #deploys · Marcus Webb', time: '14m ago' },
  { text: 'Skill extracted: Handle Enterprise Refund Request', time: '1h ago', accent: true },
  { text: 'Ingested from acmetech/platform · marcus.webb', time: '3h ago' },
]

export function DashboardMock({ className }) {
  const max = Math.max(...DEPTS.map((d) => d.count))
  return (
    <Frame title="cortex - Dashboard" className={className}>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Total Skills"
          icon={<span className="text-primary"><ClipboardIcon /></span>}
          value="28"
        >
          <span className="text-emerald-400">21 ready</span>
          {' · '}
          <span className="text-secondary">7 in review</span>
        </StatCard>
        <StatCard
          label="Documents Ingested"
          icon={<span className="text-secondary"><DocIcon size={13} /></span>}
          value="454"
        >
          across all sources
        </StatCard>
        <StatCard
          label="Data Sources"
          icon={<span className="text-emerald-400"><PlugIcon /></span>}
          value="5"
        >
          <span className="inline-flex items-center gap-1 align-middle">
            <SlackMini size={10} />
            <BrandIcon path={siGithub.path} color="#e8e8ed" size={10} />
            <BrandIcon path={siJira.path} color="#0052CC" size={10} />
            <BrandIcon path={siConfluence.path} color="#1868DB" size={10} />
          </span>
          {' connected'}
        </StatCard>
        <StatCard
          label="Avg Confidence"
          icon={<span className="text-amber-400"><GaugeIcon /></span>}
          value="74%"
          valueClass="text-amber-400"
        >
          across all skills
        </StatCard>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
            Skills by Department
          </p>
          <div className="mt-3 space-y-2.5">
            {DEPTS.map((d) => (
              <div key={d.name} className="flex items-center gap-3">
                <span className="w-20 text-[11px] text-text-dim">{d.name}</span>
                <div className="h-2 flex-1 rounded-full bg-border overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${(d.count / max) * 100}%`, background: d.color }}
                  />
                </div>
                <span className="w-5 text-right text-[11px] tabular-nums text-text-dim">
                  {d.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
            Recent Activity
          </p>
          <div className="mt-3 space-y-2.5">
            {ACTIVITY.map((a) => (
              <div key={a.text} className="flex items-start gap-2.5">
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                    a.accent ? 'bg-primary' : 'bg-border'
                  }`}
                />
                <p className="min-w-0 flex-1 truncate text-[11px] text-text-dim">
                  {a.accent ? <span className="text-text">{a.text}</span> : a.text}
                </p>
                <span className="shrink-0 text-[10px] text-text-dim/70">{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Frame>
  )
}

/* ---------- Data Sources ---------- */

const SOURCES = [
  { name: 'Slack', icon: <SlackMini size={16} />, docs: 240, connected: true },
  { name: 'GitHub', icon: <BrandIcon path={siGithub.path} color="#e8e8ed" />, docs: 96, connected: true },
  { name: 'Jira', icon: <BrandIcon path={siJira.path} color="#0052CC" />, docs: 58, connected: true },
  { name: 'Confluence', icon: <BrandIcon path={siConfluence.path} color="#1868DB" />, docs: 34, connected: true },
  { name: 'File Upload', icon: <span className="text-text-dim"><DocIcon size={16} /></span>, docs: 26, connected: true },
  { name: 'Discord', icon: <BrandIcon path={siDiscord.path} color="#5865F2" />, docs: 0, connected: false },
]

export function SourcesMock() {
  return (
    <Frame title="cortex - Data Sources">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        {SOURCES.map((s) => (
          <div key={s.name} className="rounded-xl border border-border bg-surface p-4">
            <div className="flex items-center justify-between">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-bg">
                {s.icon}
              </span>
              <span
                className={`flex items-center gap-1.5 text-[10px] font-medium ${
                  s.connected ? 'text-emerald-400' : 'text-text-dim'
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    s.connected ? 'bg-emerald-400' : 'bg-border'
                  }`}
                />
                {s.connected ? 'Connected' : 'Available'}
              </span>
            </div>
            <p className="mt-3 text-xs font-semibold text-text">{s.name}</p>
            <p className="mt-0.5 text-[10px] text-text-dim">
              {s.connected ? `${s.docs} documents` : 'Connect to ingest'}
            </p>
          </div>
        ))}
      </div>
    </Frame>
  )
}

/* ---------- Query ---------- */

const QUERY_STEPS = [
  'Deploy to staging',
  'Run smoke tests',
  'Promote to 5% canary',
  'Watch for 30-minute bake',
  'Auto-promote to full production',
]

const CHATS = [
  { title: 'How do we deploy to production?', time: 'just now', active: true },
  { title: 'What do we do when production goes down?', time: '14m ago' },
  { title: 'Handle enterprise refund request', time: '2h ago' },
]

export function QueryMock() {
  return (
    <Frame title="cortex - Query">
      <div className="flex gap-4">
        {/* Chat column */}
        <div className="min-w-0 flex-1">
          {/* user message */}
          <div className="flex justify-end">
            <div className="max-w-[80%] rounded-2xl rounded-tr-md border border-primary/30 bg-primary/20 px-4 py-2 text-xs text-text">
              How do we deploy to production?
            </div>
          </div>

          {/* assistant answer */}
          <div className="mt-4 max-w-[95%]">
            <p className="text-xs leading-relaxed text-text">
              Here's how this works. It follows the{' '}
              <span className="font-semibold text-primary">
                Deploy to Staging with Smoke Tests and Canary
              </span>{' '}
              workflow:
            </p>

            <div className="mt-3 space-y-1.5">
              {QUERY_STEPS.map((s, i) => (
                <div key={s} className="flex items-center gap-2.5">
                  <span className="flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full border border-border bg-surface text-[9px] font-semibold text-text-dim">
                    {i + 1}
                  </span>
                  <span className="text-[11px] text-text-dim">{s}</span>
                </div>
              ))}
            </div>

            <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/5 px-3 py-2 text-[10px]">
              <span className="font-medium text-amber-400">If error rate or p99 exceeds thresholds:</span>{' '}
              <span className="text-text-dim">auto-rollback</span>
            </div>

            {/* trust row */}
            <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-border/60 pt-2 text-[10px] text-text-dim">
              <span className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" /> 72% confident
              </span>
              <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 font-medium text-amber-400">
                Assisted
              </span>
              <span>9 sources ▾</span>
              <span className="ml-auto text-primary">View full skill →</span>
            </div>
          </div>

          {/* input bar */}
          <div className="mt-5 flex items-center gap-2 rounded-2xl border border-border bg-surface px-4 py-2.5">
            <span className="flex-1 text-xs text-text-dim/70">Ask anything…</span>
            <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary text-white">
              <svg viewBox="0 0 24 24" width={12} height={12} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="m22 2-7 20-4-9-9-4Z" />
              </svg>
            </span>
          </div>
        </div>

        {/* Stored chats sidebar */}
        <div className="hidden w-40 shrink-0 sm:block">
          <div className="rounded-lg bg-primary px-2 py-1.5 text-center text-[10px] font-medium text-white">
            + New chat
          </div>
          <p className="mt-3 px-1 text-[9px] font-semibold uppercase tracking-wider text-text-dim">
            Chats
          </p>
          <div className="mt-1.5 space-y-0.5">
            {CHATS.map((c) => (
              <div
                key={c.title}
                className={`rounded-lg px-2 py-1.5 ${c.active ? 'bg-surface' : ''}`}
              >
                <p className={`truncate text-[10px] ${c.active ? 'text-text' : 'text-text-dim'}`}>
                  {c.title}
                </p>
                <p className="mt-0.5 text-[9px] text-text-dim/70">{c.time}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Frame>
  )
}

/* ---------- Your Data (transparency) ---------- */

function ShieldIcon({ size = 14 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  )
}

const OVERVIEW_SOURCES = [
  { name: 'Slack', icon: <SlackMini size={12} />, docs: 240, range: 'Nov 2025 – Jun 2026' },
  { name: 'GitHub', icon: <BrandIcon path={siGithub.path} color="#e8e8ed" size={12} />, docs: 96, range: 'Dec 2025 – Jun 2026' },
  { name: 'Jira', icon: <BrandIcon path={siJira.path} color="#0052CC" size={12} />, docs: 58, range: 'Jan 2026 – Jun 2026' },
  { name: 'Confluence', icon: <BrandIcon path={siConfluence.path} color="#1868DB" size={12} />, docs: 34, range: 'Nov 2025 – May 2026' },
]

const OVERVIEW_SAMPLE = {
  snippet:
    'Reminder: staging deploys need a green smoke-test run before canary. Rollback is automatic if p99 crosses the threshold during the 30-minute bake…',
  meta: 'Marcus Webb · #deploys · Jun 24, 2026',
}

export function DataOverviewMock() {
  return (
    <Frame title="cortex - Your Data">
      {/* trust statement */}
      <div className="flex items-start gap-2.5 rounded-xl border border-emerald-400/25 bg-emerald-400/5 px-4 py-3">
        <span className="mt-0.5 text-emerald-400"><ShieldIcon /></span>
        <p className="text-[11px] leading-relaxed text-text">
          This is everything Cortex has processed from your uploads. Nothing
          beyond this has been accessed.
        </p>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {/* per-source counts + date ranges */}
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
            Ingested by source
          </p>
          <div className="mt-3 space-y-2.5">
            {OVERVIEW_SOURCES.map((s) => (
              <div key={s.name} className="flex items-center gap-2.5">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-border bg-bg">
                  {s.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-medium text-text">{s.name}</p>
                  <p className="text-[9px] text-text-dim">{s.range}</p>
                </div>
                <span className="shrink-0 text-[11px] font-semibold tabular-nums text-text">
                  {s.docs} <span className="font-normal text-text-dim">docs</span>
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* sample content + extracted skills */}
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-surface p-4">
            <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
              Sample content
            </p>
            <div className="mt-2.5 rounded-lg border border-border bg-bg px-3 py-2.5">
              <p className="text-[10px] leading-relaxed text-text">{OVERVIEW_SAMPLE.snippet}</p>
              <p className="mt-1.5 text-[9px] text-text-dim">{OVERVIEW_SAMPLE.meta}</p>
            </div>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
              Skills extracted from your data
            </p>
            <div className="mt-2.5 space-y-1.5">
              {['Deploy to Staging with Smoke Tests and Canary', 'Handle Enterprise Refund Request'].map((name) => (
                <div key={name} className="flex items-center gap-2">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                  <p className="min-w-0 flex-1 truncate text-[11px] text-text">{name}</p>
                  <span className="shrink-0 text-[10px] text-primary">View →</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Frame>
  )
}

/* ---------- Review Queue ---------- */

const QUEUE = [
  {
    name: 'Handle Enterprise Refund Request',
    description: 'Verify the invoice, get finance approval, issue the refund in Stripe',
    dept: 'support',
    confidence: 0.81,
    expanded: true,
  },
  {
    name: 'Rotate On-Call and Escalation Schedule',
    description: 'Weekly PagerDuty rotation with backup engineer and Slack announcement',
    dept: 'engineering',
    confidence: 0.74,
  },
  {
    name: 'Onboard New Enterprise Customer',
    description: 'Provision workspace, assign CSM, schedule kickoff within 5 business days',
    dept: 'sales',
    confidence: 0.68,
  },
]

export function ReviewMock() {
  return (
    <Frame title="cortex - Review Queue">
      <p className="text-xs font-semibold text-text">
        Pending review <span className="font-normal text-text-dim">({QUEUE.length})</span>
      </p>
      <div className="mt-3 space-y-2.5">
        {QUEUE.map((q) => (
          <div key={q.name} className="rounded-xl border border-border bg-surface">
            <div className="flex items-center gap-3 px-4 py-3">
              <span className="text-text-dim">{q.expanded ? '▾' : '▸'}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-semibold text-text">{q.name}</p>
                <p className="mt-0.5 truncate text-[10px] text-text-dim">{q.description}</p>
              </div>
              <DeptChip>{q.dept}</DeptChip>
              <div className="hidden sm:block">
                <ConfBar value={q.confidence} />
              </div>
            </div>
            {q.expanded && (
              <div className="flex items-center gap-2 border-t border-border px-4 py-3">
                <span className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-medium text-emerald-400">
                  ✓ Approve
                </span>
                <span className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-2.5 py-1 text-[10px] font-medium text-amber-400">
                  Edit
                </span>
                <span className="rounded-lg border border-red-400/30 bg-red-400/10 px-2.5 py-1 text-[10px] font-medium text-red-400">
                  Reject
                </span>
                <span className="ml-auto text-[10px] text-primary">Full detail ↗</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </Frame>
  )
}
