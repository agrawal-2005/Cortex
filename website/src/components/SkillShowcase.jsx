import { useState } from 'react'
import { siGithub, siJira } from 'simple-icons'

/*
 * Static, scrollable rendering of a real extracted skill (Deploy to Staging
 * with Smoke Tests and Canary). No API - data is frozen below so the demo
 * shows exactly what the product outputs. The frame is fixed-height and the
 * user scrolls ("slides up") inside it.
 */

const SKILL = {
  name: 'Deploy to Staging with Smoke Tests and Canary',
  description:
    'Deploy to staging, run smoke tests, and promote to production with a 5% canary and 30-minute bake',
  department: 'engineering',
  confidence: 0.724,
  readiness: 'assisted',
  trigger: 'manual · merge of PR to main',
  repeatable: true,
  missing_for_automation: [
    'API endpoint for auto-rollback',
    'Error dashboard monitoring automation',
    'Missing approval gate on a destructive tool',
  ],
  requires_human_review: ['Error dashboard monitoring', 'Auto-rollback decision'],
  prerequisites: ['Repository in owner/name form', 'Branch to deploy from'],
  conditions: [
    'Merge of PR to main',
    'Successful deployment to staging',
    'Successful smoke tests',
    'Successful canary promotion',
  ],
  roles: ['backend engineer', 'devops'],
  edge_cases: [
    'Auth service returns 503 for ~2 minutes after every staging deploy',
    'Error rate or p99 exceeds thresholds during bake',
  ],
  steps: [
    {
      action: 'Deploy to staging',
      explanation: 'Deploy the artifact to staging',
      tool: 'Makefile',
      method: 'make deploy ENV=staging',
      inputs: ['repo', 'branch'],
      expected: 'Deployment to staging successful',
      success: 'Deployment to staging successful',
      confidence: 0.49,
      on_failure: { if: 'deployment fails', then: 'retry deployment' },
      sources: [
        {
          kind: 'file',
          author: 'Elena Petrov',
          date: 'Nov 20, 2025',
          quote: 'Deploy the artifact to staging with `make deploy ENV=staging`.',
        },
      ],
    },
    {
      action: 'Run smoke tests',
      explanation: 'Run smoke tests against staging',
      tool: 'Makefile',
      method: 'make smoke',
      inputs: ['repo', 'branch'],
      expected: 'Smoke tests pass',
      success: 'All 14 smoke checks pass',
      confidence: 0.85,
      on_failure: { if: 'smoke tests fail', then: 'stop deployment' },
      sources: [
        {
          kind: 'jira',
          author: 'Marcus Webb',
          date: 'Jun 26, 2026',
          quote: '`make smoke` against staging',
        },
        {
          kind: 'slack',
          author: 'Marcus Webb',
          date: 'Jun 2, 2026',
          quote:
            'run the smoke tests first. `make smoke` against staging. If any of the 14 checks fail, the deploy stops there.',
        },
      ],
    },
    {
      action: 'Promote to 5% canary',
      explanation: 'Promote to 5% canary',
      tool: 'Makefile',
      method: 'make deploy ENV=prod CANARY=5',
      inputs: ['repo', 'branch'],
      expected: 'Canary promotion successful',
      success: 'Canary promotion successful',
      confidence: 0.78,
      on_failure: { if: 'canary promotion fails', then: 'stop deployment' },
      sources: [
        {
          kind: 'slack',
          author: 'Marcus Webb',
          date: 'Jun 2, 2026',
          quote: 'promote 5% with `make deploy ENV=prod CANARY=5`',
        },
        {
          kind: 'github',
          author: 'marcus.webb',
          date: 'Jun 20, 2026',
          quote:
            'canary promote is manual: deploy to staging, run smoke tests, promote 5% with `make deploy ENV=prod CANARY=5`',
        },
      ],
    },
    {
      action: 'Watch for 30-minute bake',
      explanation: 'Watch the error dashboard for 30 minutes',
      tool: 'Error dashboard',
      method: 'manual monitoring',
      inputs: [],
      expected: 'Error rate and p99 within thresholds',
      success: 'Error rate < 2% and p99 < 800ms sustained over 5 minutes',
      confidence: 0.72,
      on_failure: { if: 'error rate or p99 exceeds thresholds', then: 'auto-rollback' },
      sources: [
        {
          kind: 'jira',
          author: 'Marcus Webb',
          date: 'Jun 26, 2026',
          quote: 'watch the error dashboard for the 30-min bake',
        },
        {
          kind: 'github',
          author: 'marcus.webb',
          date: 'Jun 20, 2026',
          quote:
            'error rate >2% sustained over 5 minutes OR p99 >800ms sustained over 5 minutes triggers auto-rollback',
        },
      ],
    },
    {
      action: 'Auto-promote to full production',
      explanation: 'Auto-promote to full production if error rate and p99 within thresholds',
      tool: 'Makefile',
      method: 'make deploy ENV=prod',
      inputs: ['repo', 'branch'],
      expected: 'Full production deployment successful',
      success: 'Full production deployment successful',
      confidence: 0.78,
      on_failure: { if: 'full production deployment fails', then: 'stop deployment' },
      sources: [
        {
          kind: 'slack',
          author: 'Marcus Webb',
          date: 'Jun 2, 2026',
          quote: 'automatic promote if metrics stay clean for 30 min',
        },
        {
          kind: 'github',
          author: 'marcus.webb',
          date: 'Jun 20, 2026',
          quote:
            'canary promote is manual: deploy to staging, run smoke tests, promote 5%, watch the error dashboard for the 30-min bake, then full rollout',
        },
      ],
    },
  ],
}

/* Exact API response for this skill - shown in the Raw JSON tab. */
const RAW_SKILL = {
  schema_version: '1.0',
  skill_id: '278ccbb9-4f0d-4db9-bf4b-ac92379a81fc',
  name: 'Deploy to Staging with Smoke Tests and Canary',
  description:
    'Deploy to staging, run smoke tests, and promote to production with a 5% canary and 30-minute bake',
  department: 'engineering',
  confidence: 0.724,
  trigger: { type: 'manual', condition: 'merge of PR to main', event_binding: null },
  inputs_schema: { repo: 'repository in owner/name form', branch: 'branch to deploy from' },
  automation_readiness: {
    level: 'assisted',
    safe_to_automate: false,
    missing_for_automation: [
      'API endpoint for auto-rollback',
      'Error dashboard monitoring automation',
      'missing approval gate: skill uses a money-moving or destructive tool but no step has an approval_gate',
    ],
    requires_human_review: ['Error dashboard monitoring', 'Auto-rollback decision'],
  },
  is_repeatable: true,
  prerequisites: ['Repository in owner/name form', 'Branch to deploy from'],
  conditions: [
    'Merge of PR to main',
    'Successful deployment to staging',
    'Successful smoke tests',
    'Successful canary promotion',
  ],
  roles_required: ['backend engineer', 'devops'],
  execution_plan: [
    {
      step_id: '0da6f579-4734-4a95-800d-2b92a4b8e27d',
      order: 1,
      action: 'Deploy to staging',
      explanation: 'Deploy the artifact to staging',
      tool: { name: 'Makefile', method: 'make deploy ENV=staging', auth_required: null },
      tools: [],
      inputs_required: ['repo', 'branch'],
      parameters: {},
      command: 'make deploy ENV=staging',
      conditions: null,
      expected_output: 'Deployment to staging successful',
      success_criteria: 'Deployment to staging successful',
      on_failure: [{ if: 'deployment fails', then: 'retry deployment', target: null }],
      branch: {},
      approval_gate: {},
      confidence: 0.49,
      depends_on: [],
      status: 'pending',
    },
    {
      step_id: '30a656c5-f6f7-4a39-8225-62d735331670',
      order: 2,
      action: 'Run smoke tests',
      explanation: 'Run smoke tests against staging',
      tool: { name: 'Makefile', method: 'make smoke', auth_required: null },
      tools: [],
      inputs_required: ['repo', 'branch'],
      parameters: {},
      command: 'make smoke',
      conditions: null,
      expected_output: 'Smoke tests pass',
      success_criteria: 'All 14 smoke checks pass',
      on_failure: [{ if: 'smoke tests fail', then: 'stop deployment', target: null }],
      branch: {},
      approval_gate: {},
      confidence: 0.85,
      depends_on: [],
      status: 'pending',
    },
    {
      step_id: '7fb764fb-8359-488d-8c71-e255d9499616',
      order: 3,
      action: 'Promote to 5% canary',
      explanation: 'Promote to 5% canary',
      tool: { name: 'Makefile', method: 'make deploy ENV=prod CANARY=5', auth_required: null },
      tools: [],
      inputs_required: ['repo', 'branch'],
      parameters: {},
      command: 'make deploy ENV=prod CANARY=5',
      conditions: null,
      expected_output: 'Canary promotion successful',
      success_criteria: 'Canary promotion successful',
      on_failure: [{ if: 'canary promotion fails', then: 'stop deployment', target: null }],
      branch: {},
      approval_gate: {},
      confidence: 0.78,
      depends_on: [],
      status: 'pending',
    },
    {
      step_id: '9ce58487-1249-420a-9e90-08dc31f60270',
      order: 4,
      action: 'Watch for 30-minute bake',
      explanation: 'Watch the error dashboard for 30 minutes',
      tool: { name: 'Error dashboard', method: 'manual monitoring', auth_required: null },
      tools: [],
      inputs_required: [],
      parameters: {},
      command: null,
      conditions: null,
      expected_output: 'Error rate and p99 within thresholds',
      success_criteria: 'Error rate < 2% and p99 < 800ms sustained over 5 minutes',
      on_failure: [
        { if: 'error rate or p99 exceeds thresholds', then: 'auto-rollback', target: null },
      ],
      branch: {},
      approval_gate: {},
      confidence: 0.72,
      depends_on: [],
      status: 'pending',
    },
    {
      step_id: '2189b10b-1e84-4308-b481-67d87e98487c',
      order: 5,
      action: 'Auto-promote to full production',
      explanation: 'Auto-promote to full production if error rate and p99 within thresholds',
      tool: { name: 'Makefile', method: 'make deploy ENV=prod', auth_required: null },
      tools: [],
      inputs_required: ['repo', 'branch'],
      parameters: {},
      command: 'make deploy ENV=prod',
      conditions: null,
      expected_output: 'Full production deployment successful',
      success_criteria: 'Full production deployment successful',
      on_failure: [
        { if: 'full production deployment fails', then: 'stop deployment', target: null },
      ],
      branch: {},
      approval_gate: {},
      confidence: 0.78,
      depends_on: [],
      status: 'pending',
    },
  ],
  edge_cases: [
    'Auth service returns 503 for ~2 minutes after every staging deploy',
    'Error rate or p99 exceeds thresholds during bake',
  ],
  total_steps: 5,
  estimated_confidence: 0.724,
}

/* ---------- tiny icons (inline, no icon lib on the website) ---------- */

function WrenchIcon({ size = 13 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  )
}

function ShieldIcon({ size = 13 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
    </svg>
  )
}

export function DocIcon({ size = 12 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6" />
    </svg>
  )
}

export function SlackMini({ size = 12 }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden>
      <path fill="#E01E5A" d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" />
      <path fill="#36C5F0" d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" />
      <path fill="#2EB67D" d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" />
      <path fill="#ECB22E" d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
    </svg>
  )
}

function SourceIcon({ kind }) {
  if (kind === 'slack') return <SlackMini />
  if (kind === 'github')
    return (
      <svg viewBox="0 0 24 24" width={12} height={12} fill="#e8e8ed" aria-hidden>
        <path d={siGithub.path} />
      </svg>
    )
  if (kind === 'jira')
    return (
      <svg viewBox="0 0 24 24" width={12} height={12} fill="#0052CC" aria-hidden>
        <path d={siJira.path} />
      </svg>
    )
  return (
    <span className="text-text-dim">
      <DocIcon />
    </span>
  )
}

/* ---------- raw JSON view (lightweight syntax highlighting) ---------- */

const TOKEN_RE = /("(?:[^"\\]|\\.)*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:e[+-]?\d+)?)/g

function JsonView({ value }) {
  const json = JSON.stringify(value, null, 2)
  const nodes = []
  let last = 0
  let key = 0
  for (const m of json.matchAll(TOKEN_RE)) {
    if (m.index > last) nodes.push(json.slice(last, m.index))
    if (m[1] !== undefined) {
      // string - purple when it's a key, cyan when it's a value
      nodes.push(
        <span key={key++} className={m[2] ? 'text-[#a78bfa]' : 'text-secondary/80'}>
          {m[1]}
        </span>
      )
      if (m[2]) nodes.push(m[2])
    } else if (m[3] !== undefined) {
      nodes.push(
        <span key={key++} className="text-amber-400/90">
          {m[3]}
        </span>
      )
    } else {
      nodes.push(
        <span key={key++} className="text-emerald-400/90">
          {m[4]}
        </span>
      )
    }
    last = m.index + m[0].length
  }
  nodes.push(json.slice(last))
  return (
    <pre className="whitespace-pre font-mono text-[11px] leading-relaxed text-text-dim">
      {nodes}
    </pre>
  )
}

/* ---------- pieces ---------- */

function confColor(c) {
  if (c < 0.6) return 'bg-red-400'
  if (c < 0.75) return 'bg-amber-400'
  return 'bg-emerald-400'
}

function confText(c) {
  if (c < 0.6) return 'text-red-400'
  if (c < 0.75) return 'text-amber-400'
  return 'text-emerald-400'
}

function ConfidenceBar({ value }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-40 h-1.5 rounded-full bg-border overflow-hidden">
        <div
          className={`h-full rounded-full ${confColor(value)}`}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className={`text-xs font-medium ${confText(value)}`}>
        {Math.round(value * 100)}%
      </span>
    </div>
  )
}

function Chip({ children }) {
  return (
    <span className="inline-flex items-center rounded-md border border-border bg-bg px-1.5 py-0.5 font-mono text-[10px] text-text-dim">
      {children}
    </span>
  )
}

function SourceRow({ source }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-border bg-bg/70 px-3 py-2">
      <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-surface border border-border">
        <SourceIcon kind={source.kind} />
      </span>
      <div className="min-w-0">
        <p className="text-[11px]">
          <span className="font-medium text-text">{source.author}</span>
          <span className="text-text-dim"> · {source.date}</span>
        </p>
        <p className="mt-0.5 text-[11px] leading-relaxed text-text-dim">{source.quote}</p>
      </div>
    </div>
  )
}

function Step({ step, order }) {
  return (
    <div className="relative pl-10">
      {/* timeline */}
      <span className="absolute left-0 top-0 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-[11px] font-semibold text-white">
        {order}
      </span>
      <span className="absolute left-3 top-7 bottom-[-24px] w-px bg-border" aria-hidden />

      <div className="rounded-xl border border-border bg-surface p-4">
        <h4 className="text-sm font-semibold text-text">{step.action}</h4>
        <p className="mt-1 text-xs text-text-dim">{step.explanation}</p>

        <div className="mt-3 flex items-center gap-2 rounded-lg border border-border bg-bg/70 px-3 py-2 text-xs">
          <span className="text-secondary">
            <WrenchIcon />
          </span>
          <span className="font-medium text-text">{step.tool}</span>
          <span className="text-text-dim">· {step.method}</span>
        </div>

        {step.inputs.length > 0 && (
          <p className="mt-2.5 flex items-center gap-1.5 text-[11px]">
            <span className="font-medium text-text">Inputs:</span>
            {step.inputs.map((i) => (
              <Chip key={i}>{i}</Chip>
            ))}
          </p>
        )}

        <p className="mt-2 text-[11px]">
          <span className="font-medium text-text">Expected output: </span>
          <span className="text-text-dim">{step.expected}</span>
        </p>
        <p className="mt-1 text-[11px]">
          <span className="font-medium text-text">Success when: </span>
          <span className="text-text-dim">{step.success}</span>
        </p>

        <div className="mt-2.5">
          <ConfidenceBar value={step.confidence} />
        </div>

        <p className="mt-3 text-[10px] font-medium uppercase tracking-wider text-text-dim">
          Sources ({step.sources.length})
        </p>
        <div className="mt-1.5 space-y-1.5">
          {step.sources.map((s) => (
            <SourceRow key={s.quote} source={s} />
          ))}
        </div>

        <div className="mt-2.5 flex items-center gap-2 rounded-lg border border-amber-400/25 bg-amber-400/5 px-3 py-2 text-[11px]">
          <span className="text-amber-400">
            <ShieldIcon />
          </span>
          <span>
            <span className="font-medium text-amber-400">If {step.on_failure.if}:</span>{' '}
            <span className="text-text-dim">{step.on_failure.then}</span>
          </span>
        </div>
      </div>
    </div>
  )
}

/* ---------- showcase ---------- */

const VIEW_TABS = [
  { id: 'readable', label: 'Readable' },
  { id: 'json', label: 'Raw JSON' },
]

export default function SkillShowcase() {
  const [view, setView] = useState('readable')

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface">
      {/* browser chrome */}
      <div className="flex items-center gap-1.5 border-b border-border px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#FEBC2E]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28C840]" />
        <span className="ml-3 text-[11px] text-text-dim">cortex - Skills</span>
        <div className="ml-auto flex items-center gap-1 rounded-lg border border-border bg-bg p-0.5">
          {VIEW_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setView(t.id)}
              className={`rounded-md px-2 py-1 text-[10px] font-medium transition-colors ${
                view === t.id
                  ? 'bg-primary/15 text-primary'
                  : 'text-text-dim hover:text-text'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* scrollable output */}
      <div className="relative">
        {view === 'json' ? (
          <div className="h-[540px] overflow-auto bg-bg/60 p-5 sm:p-6">
            <JsonView value={RAW_SKILL} />
          </div>
        ) : (
        <div className="h-[540px] overflow-y-auto bg-bg/60 p-5 sm:p-6">
          {/* skill header */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-text-dim">
              engineering
            </span>
            <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-medium text-amber-400">
              Assisted
            </span>
            <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-text-dim">
              Repeatable
            </span>
            <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-text-dim">
              Trigger: {SKILL.trigger}
            </span>
          </div>

          <h3 className="mt-3 text-lg font-semibold tracking-tight text-text">{SKILL.name}</h3>
          <p className="mt-1 text-xs leading-relaxed text-text-dim">{SKILL.description}</p>
          <div className="mt-3">
            <ConfidenceBar value={SKILL.confidence} />
          </div>

          {/* automation readiness */}
          <div className="mt-5 rounded-xl border border-border bg-surface p-4">
            <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
              Automation Readiness
            </p>
            <div className="mt-2 grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-[11px] font-medium text-text">Missing for automation</p>
                <ul className="mt-1.5 space-y-1">
                  {SKILL.missing_for_automation.map((m) => (
                    <li key={m} className="flex gap-2 text-[11px] text-text-dim">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-400" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-[11px] font-medium text-text">Requires human review</p>
                <ul className="mt-1.5 space-y-1">
                  {SKILL.requires_human_review.map((m) => (
                    <li key={m} className="flex gap-2 text-[11px] text-text-dim">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-secondary" />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* prerequisites / applies when */}
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-surface p-4">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
                Prerequisites
              </p>
              <ul className="mt-2 space-y-1">
                {SKILL.prerequisites.map((p) => (
                  <li key={p} className="flex gap-2 text-[11px] text-text-dim">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-surface p-4">
              <p className="text-[10px] font-medium uppercase tracking-wider text-text-dim">
                Applies When
              </p>
              <ul className="mt-2 space-y-1">
                {SKILL.conditions.map((c) => (
                  <li key={c} className="flex gap-2 text-[11px] text-text-dim">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* roles */}
          <div className="mt-4 flex items-center gap-1.5">
            {SKILL.roles.map((r) => (
              <Chip key={r}>{r}</Chip>
            ))}
          </div>

          {/* steps */}
          <p className="mt-6 text-sm font-semibold text-text">
            Steps <span className="font-normal text-text-dim">({SKILL.steps.length})</span>
          </p>
          <div className="mt-4 space-y-6">
            {SKILL.steps.map((step, i) => (
              <Step key={step.action} step={step} order={i + 1} />
            ))}
          </div>

          {/* edge cases */}
          <p className="mt-8 text-sm font-semibold text-text">Edge Cases</p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {SKILL.edge_cases.map((e) => (
              <div
                key={e}
                className="rounded-lg border border-amber-400/25 bg-amber-400/5 px-3 py-2.5 text-[11px] text-text-dim"
              >
                {e}
              </div>
            ))}
          </div>
        </div>
        )}

        {/* bottom fade hinting there's more to scroll */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-bg to-transparent" />
      </div>
    </div>
  )
}
