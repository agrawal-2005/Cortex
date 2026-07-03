import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft, Copy, Check, AlertTriangle, ShieldAlert, ListChecks,
  ExternalLink, FileJson, BookOpen, Users,
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

function Step({ step, isLast }) {
  const details = step.details || {}
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
        {details.expected_output && (
          <p className="text-xs text-text-dim">
            <span className="font-medium text-text">Expected output:</span> {details.expected_output}
          </p>
        )}
        {Array.isArray(details.tools) && details.tools.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {details.tools.map((t) => <ToolBadge key={t}>{t}</ToolBadge>)}
          </div>
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
        {details.on_failure && (
          <div className="flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/[0.06] px-3 py-2.5">
            <ShieldAlert size={14} className="text-warning shrink-0 mt-0.5" />
            <p className="text-xs text-text-dim">
              <span className="font-medium text-warning">If this fails:</span>{' '}
              {typeof details.on_failure === 'string'
                ? details.on_failure
                : JSON.stringify(details.on_failure)}
            </p>
          </div>
        )}
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
          {/* Prerequisites */}
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
              GET /api/skills/{id}/executable — consumed by AI agents
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
