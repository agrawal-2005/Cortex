import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, Copy, Check, AlertTriangle, ShieldAlert, ListChecks,
  ExternalLink, FileJson, BookOpen, Users, Wrench, Zap, Repeat,
  Bot, KeyRound, GitBranch, UserCheck,
} from 'lucide-react'
import { getSkill, getExecutableSkill } from '../api/client'
import {
  StatusBadge, DeptBadge, ToolBadge, ConfidenceBar, Skeleton, EmptyState,
} from '../components/Primitives'
import SourceIcon from '../components/SourceIcon'
import { useToast } from '../components/Toast'
import { formatDate } from '../lib/ui'

// ── Minimal JSON syntax highlighter ───────────────────────────────────

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlightJson(obj) {
  const json = escapeHtml(JSON.stringify(obj, null, 2))
  return json.replace(
    /("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let color = '#00D2FF' // numbers
      if (/^"/.test(match)) {
        color = /:$/.test(match) ? '#6C5CE7' : '#00E676' // keys : strings
      } else if (/true|false/.test(match)) {
        color = '#FFB300'
      } else if (/null/.test(match)) {
        color = '#FF5252'
      }
      return `<span style="color:${color}">${match}</span>`
    },
  )
}

// ── Step source reference ─────────────────────────────────────────────

function SourceRef({ source }) {
  const inner = (
    <div className="flex items-start gap-2.5 bg-bg border border-border rounded-lg px-3 py-2.5 hover:border-primary/40 transition-colors">
      <span className="w-6 h-6 rounded-md bg-surface-2 border border-border flex items-center justify-center shrink-0 mt-0.5">
        <SourceIcon name={source.source_type} size={12} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[11px] text-text-dim">
          <span className="font-medium text-text">{source.author_name || 'Unknown author'}</span>
          <span>·</span>
          <span>{formatDate(source.created_at)}</span>
          {source.source_link && <ExternalLink size={10} className="text-primary" />}
        </div>
        {source.snippet && (
          <p className="text-xs text-text-dim mt-1 line-clamp-2">{source.snippet}</p>
        )}
      </div>
    </div>
  )
  return source.source_link ? (
    <a href={source.source_link} target="_blank" rel="noreferrer" className="block">
      {inner}
    </a>
  ) : inner
}

// ── Step (timeline entry) ─────────────────────────────────────────────

function OnFailure({ onFailure }) {
  // Normalize: string | {if, then} | [{if, then}, ...]
  const rules = (Array.isArray(onFailure) ? onFailure : [onFailure])
    .map((r) => (typeof r === 'string' ? { then: r } : r))
    .filter((r) => r && (r.if || r.then))
  if (rules.length === 0) return null
  return (
    <div className="rounded-lg border border-warning/25 bg-warning/[0.06] px-3 py-2.5 space-y-1.5">
      {rules.map((r, i) => (
        <div key={i} className="flex items-start gap-2">
          <ShieldAlert size={14} className="text-warning shrink-0 mt-0.5" />
          <p className="text-xs text-text-dim leading-relaxed">
            <span className="font-medium text-warning">
              {r.if ? `If ${r.if}:` : 'On failure:'}
            </span>{' '}
            {r.then}
          </p>
        </div>
      ))}
    </div>
  )
}

function Step({ step, isLast }) {
  const details = step.details || {}
  const tool = details.tool
  const inputs = details.inputs_required || []
  return (
    <li className="relative pl-12 pb-8">
      {!isLast && (
        <span className="absolute left-[15px] top-9 bottom-0 w-px bg-border" aria-hidden />
      )}
      <span className="absolute left-0 top-0 w-8 h-8 rounded-full gradient-brand flex items-center justify-center text-[13px] font-bold text-white shadow-lg shadow-primary/20">
        {step.step_order}
      </span>
      <div className="card p-4 space-y-3">
        <p className="text-sm font-semibold text-text">{step.action}</p>
        {details.explanation && (
          <p className="text-sm text-text-dim leading-relaxed">{details.explanation}</p>
        )}
        {tool?.name && (
          <div className="flex items-start gap-2.5 bg-bg border border-border rounded-lg px-3 py-2.5">
            <Wrench size={14} className="text-secondary shrink-0 mt-0.5" />
            <div className="min-w-0 text-xs space-y-0.5">
              <p className="text-text">
                <span className="font-semibold">{tool.name}</span>
                {tool.method && <span className="text-text-dim"> · {tool.method}</span>}
              </p>
              {tool.auth_required && (
                <p className="text-text-dim flex items-center gap-1">
                  <KeyRound size={11} /> Requires {tool.auth_required}
                </p>
              )}
            </div>
          </div>
        )}
        {Array.isArray(details.tools) && details.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {details.tools.map((t) => <ToolBadge key={t}>{t}</ToolBadge>)}
          </div>
        )}
        {inputs.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap text-xs text-text-dim">
            <span className="font-medium text-text">Inputs:</span>
            {inputs.map((inp) => <ToolBadge key={inp}>{inp}</ToolBadge>)}
          </div>
        )}
        {details.expected_output && (
          <p className="text-xs text-text-dim">
            <span className="font-medium text-text">Expected output:</span> {details.expected_output}
          </p>
        )}
        {details.success_criteria && (
          <p className="text-xs text-text-dim">
            <span className="font-medium text-text">Success when:</span> {details.success_criteria}
          </p>
        )}
        <ConfidenceBar value={step.confidence} className="max-w-56" />
        {step.sources?.length > 0 && (
          <div className="space-y-1.5 pt-1">
            <p className="text-[11px] font-medium text-text-dim uppercase tracking-wider">
              Sources ({step.sources.length})
            </p>
            {step.sources.map((s, i) => <SourceRef key={i} source={s} />)}
          </div>
        )}
        {details.on_failure && <OnFailure onFailure={details.on_failure} />}
      </div>
    </li>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function SkillDetail() {
  const { id } = useParams()
  const [skill, setSkill] = useState(null)
  const [executable, setExecutable] = useState(null)
  const [tab, setTab] = useState('readable')
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState(null)
  const toast = useToast()

  useEffect(() => {
    getSkill(id)
      .then((res) => setSkill(res.data))
      .catch((e) => setError(e.response?.status === 404 ? 'Skill not found' : e.message))
    getExecutableSkill(id)
      .then((res) => setExecutable(res.data))
      .catch(() => {})
  }, [id])

  const highlighted = useMemo(
    () => (executable ? highlightJson(executable) : ''),
    [executable],
  )

  const copyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(executable, null, 2))
      setCopied(true)
      toast('Executable JSON copied to clipboard.')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast('Could not copy to clipboard.', 'error')
    }
  }

  if (error) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title={error}
        action={
          <Link to="/skills" className="text-sm text-primary hover:underline">
            ← Back to skills
          </Link>
        }
      />
    )
  }

  if (!skill) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  const steps = [...(skill.steps || [])].sort((a, b) => a.step_order - b.step_order)
  const readiness = skill.automation_readiness || {}
  const inputEntries = Object.entries(skill.inputs_schema || {})

  return (
    <div className="space-y-6">
      <Link to="/skills" className="inline-flex items-center gap-1.5 text-sm text-text-dim hover:text-text transition-colors">
        <ArrowLeft size={14} /> All skills
      </Link>

      <header className="space-y-3">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1 className="text-2xl font-bold text-text">{skill.name}</h1>
          <div className="flex items-center gap-2">
            <DeptBadge department={skill.department} />
            <StatusBadge status={skill.status} />
          </div>
        </div>
        <p className="text-sm text-text-dim max-w-3xl leading-relaxed">{skill.description}</p>
        <div className="flex items-center gap-2 flex-wrap text-xs text-text-dim">
          {skill.trigger?.type && (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full border border-border bg-surface">
              <Zap size={11} className="text-warning" />
              <span className="capitalize font-medium text-text">{skill.trigger.type}</span>
              {skill.trigger.condition && <span>· {skill.trigger.condition}</span>}
            </span>
          )}
          {skill.is_repeatable != null && (
            <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full border border-border bg-surface">
              <Repeat size={11} className={skill.is_repeatable ? 'text-success' : 'text-text-dim'} />
              {skill.is_repeatable ? 'Repeatable' : 'Not repeatable'}
            </span>
          )}
        </div>
        <div className="max-w-72">
          <ConfidenceBar value={skill.confidence} />
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface border border-border rounded-lg p-1 w-fit">
        {[
          ['readable', 'Human Readable', BookOpen],
          ['json', 'Executable JSON', FileJson],
        ].map(([key, label, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm transition-colors ${
              tab === key ? 'bg-primary/20 text-primary font-medium' : 'text-text-dim hover:text-text'
            }`}
          >
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {tab === 'readable' ? (
        <div className="space-y-8">
          {/* Automation readiness */}
          {readiness?.level && (
            <section className="card p-5 space-y-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <h2 className="text-sm font-semibold text-text flex items-center gap-2">
                  <Bot size={15} className="text-primary" /> Automation Readiness
                </h2>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border capitalize ${
                  readiness.safe_to_automate
                    ? 'border-success/30 bg-success/10 text-success'
                    : 'border-warning/30 bg-warning/10 text-warning'
                }`}>
                  {readiness.level}{readiness.safe_to_automate ? ' · safe to automate' : ' · human in the loop'}
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {readiness.missing_for_automation?.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium text-text-dim uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <GitBranch size={11} /> Missing for full automation
                    </p>
                    <ul className="space-y-1">
                      {readiness.missing_for_automation.map((m, i) => (
                        <li key={i} className="text-xs text-text-dim flex gap-2">
                          <span className="text-warning">•</span> {m}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {readiness.requires_human_review?.length > 0 && (
                  <div>
                    <p className="text-[11px] font-medium text-text-dim uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                      <UserCheck size={11} /> Requires human review
                    </p>
                    <ul className="space-y-1">
                      {readiness.requires_human_review.map((r, i) => (
                        <li key={i} className="text-xs text-text-dim flex gap-2">
                          <span className="text-secondary">•</span> {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Inputs */}
          {inputEntries.length > 0 && (
            <section className="card p-5">
              <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-3">
                <KeyRound size={15} className="text-secondary" /> Inputs
              </h2>
              <dl className="space-y-2">
                {inputEntries.map(([key, desc]) => (
                  <div key={key} className="flex items-baseline gap-3">
                    <dt><ToolBadge>{key}</ToolBadge></dt>
                    <dd className="text-sm text-text-dim">{desc}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {/* Prerequisites & Conditions */}
          {(skill.prerequisites?.length > 0 || skill.conditions?.length > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {skill.prerequisites?.length > 0 && (
                <section className="card p-5">
                  <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-3">
                    <ListChecks size={15} className="text-secondary" /> Prerequisites
                  </h2>
                  <ul className="space-y-1.5">
                    {skill.prerequisites.map((p, i) => (
                      <li key={i} className="text-sm text-text-dim flex gap-2">
                        <span className="text-secondary">•</span> {typeof p === 'string' ? p : JSON.stringify(p)}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {skill.conditions?.length > 0 && (
                <section className="card p-5">
                  <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-3">
                    <GitBranch size={15} className="text-primary" /> Applies When
                  </h2>
                  <ul className="space-y-1.5">
                    {skill.conditions.map((c, i) => (
                      <li key={i} className="text-sm text-text-dim flex gap-2">
                        <span className="text-primary">•</span> {typeof c === 'string' ? c : JSON.stringify(c)}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}

          {/* Roles */}
          {skill.roles_involved?.length > 0 && (
            <section className="flex items-center gap-2 flex-wrap text-sm text-text-dim">
              <Users size={14} />
              {skill.roles_involved.map((r, i) => <ToolBadge key={i}>{r}</ToolBadge>)}
            </section>
          )}

          {/* Steps timeline */}
          <section>
            <h2 className="text-sm font-semibold text-text mb-4">
              Steps <span className="text-text-dim font-normal">({steps.length})</span>
            </h2>
            <ol>
              {steps.map((step, i) => (
                <Step key={step.step_order} step={step} isLast={i === steps.length - 1} />
              ))}
            </ol>
          </section>

          {/* Edge cases */}
          {skill.edge_cases?.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-3">
                <AlertTriangle size={15} className="text-warning" /> Edge Cases
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {skill.edge_cases.map((e, i) => (
                  <div key={i} className="rounded-card border border-warning/25 bg-warning/[0.06] px-4 py-3">
                    <p className="text-sm text-text-dim">
                      {typeof e === 'string' ? e : JSON.stringify(e)}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      ) : (
        <section className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-surface-2">
            <p className="text-xs text-text-dim font-mono">
              GET /api/skills/{id}/executable · consumed by AI agents
            </p>
            <button
              onClick={copyJson}
              disabled={!executable}
              className="flex items-center gap-1.5 text-xs text-text-dim hover:text-text transition-colors disabled:opacity-50"
            >
              {copied ? <Check size={13} className="text-success" /> : <Copy size={13} />}
              {copied ? 'Copied' : 'Copy to clipboard'}
            </button>
          </div>
          {executable ? (
            <pre
              className="p-5 text-xs font-mono leading-relaxed overflow-x-auto text-text"
              dangerouslySetInnerHTML={{ __html: highlighted }}
            />
          ) : (
            <div className="p-5 space-y-2">
              {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-3 w-full" />)}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
