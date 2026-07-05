import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Database, ShieldCheck } from 'lucide-react'
import { getDataOverview } from '../api/client'
import { formatDate, sourceKeyOf } from '../lib/ui'
import SourceIcon from '../components/SourceIcon'
import { EmptyState, SkeletonCard, StatusBadge, ToolBadge } from '../components/Primitives'

// "github_pr" → "GitHub PR", "slack" → "Slack"
const WORD_OVERRIDES = { github: 'GitHub', pr: 'PR', api: 'API', csv: 'CSV', json: 'JSON', ms: 'MS' }
function sourceLabel(sourceType) {
  return (sourceType || '')
    .split('_')
    .map((w) => WORD_OVERRIDES[w] || w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

function dateRangeLabel(earliest, latest) {
  if (!earliest && !latest) return '-'
  return `${formatDate(earliest)} – ${formatDate(latest)}`
}

function StatCard({ label, value }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-text-dim uppercase tracking-wider">{label}</p>
      <p className="text-xl font-bold text-text mt-1 tabular-nums">{value}</p>
    </div>
  )
}

function SourceCard({ source }) {
  const { source_type, document_count, earliest, latest, samples } = source
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-bg border border-border flex items-center justify-center shrink-0">
          <SourceIcon name={sourceKeyOf(source_type)} size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text">{sourceLabel(source_type)}</h3>
          <p className="text-xs text-text-dim mt-0.5">{dateRangeLabel(earliest, latest)}</p>
        </div>
        <span className="text-sm font-semibold text-text tabular-nums shrink-0">
          {document_count} <span className="text-xs font-normal text-text-dim">documents</span>
        </span>
      </div>

      {samples.length > 0 && (
        <div className="mt-4 space-y-2">
          <p className="text-[11px] font-medium text-text-dim uppercase tracking-wider">Sample content</p>
          {samples.map((s) => (
            <div key={s.id} className="bg-bg border border-border rounded-lg px-3 py-2.5">
              <p className="text-xs text-text leading-relaxed">{s.snippet}</p>
              <p className="text-[11px] text-text-dim mt-1.5">
                {[s.author_name, s.channel_or_project, formatDate(s.created_at)]
                  .filter(Boolean)
                  .join(' · ')}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function DataOverview() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDataOverview()
      .then((res) => setData(res.data))
      .catch((e) => setError(e.response?.data?.detail || e.message))
  }, [])

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-text">Your Data</h1>
        <p className="text-sm text-text-dim mt-1">
          A full account of what Cortex has ingested.
        </p>
      </header>

      {/* Trust statement */}
      <div className="card p-5 border-success/30 flex items-start gap-3">
        <ShieldCheck size={18} className="text-success shrink-0 mt-0.5" />
        <p className="text-sm text-text">
          This is everything Cortex has processed from your uploads. Nothing
          beyond this has been accessed.
        </p>
      </div>

      {error && (
        <div className="card p-5 border-danger/30">
          <p className="text-sm text-danger">Couldn't load data overview: {error}</p>
        </div>
      )}

      {!data && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
        </div>
      )}

      {data && data.total_documents === 0 && (
        <EmptyState
          icon={Database}
          title="Nothing ingested yet"
          message="Connect a source and everything Cortex processes will be listed here."
          action={
            <Link to="/sources" className="text-sm text-primary hover:underline flex items-center gap-1">
              Go to Data Sources <ArrowRight size={13} />
            </Link>
          }
        />
      )}

      {data && data.total_documents > 0 && (
        <>
          {/* Headline stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard label="Documents" value={data.total_documents} />
            <StatCard label="Sources" value={data.sources.length} />
            <StatCard
              label="Date range"
              value={dateRangeLabel(data.date_range.earliest, data.date_range.latest)}
            />
          </div>

          {/* Per-source breakdown */}
          <section>
            <h2 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3">
              Ingested by source
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {data.sources.map((source) => (
                <SourceCard key={source.source_type} source={source} />
              ))}
            </div>
          </section>

          {/* Skills extracted from this data */}
          <section>
            <h2 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3">
              Skills extracted from your data
            </h2>
            {data.skills.length === 0 ? (
              <p className="text-sm text-text-dim">No skills extracted yet.</p>
            ) : (
              <div className="card divide-y divide-border">
                {data.skills.map((skill) => (
                  <Link
                    key={skill.id}
                    to={`/skills/${skill.id}`}
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-surface-2 transition-colors group"
                  >
                    <span className="text-sm text-text font-medium flex-1 min-w-0 truncate group-hover:text-primary transition-colors">
                      {skill.name}
                    </span>
                    <span className="hidden sm:flex items-center gap-1.5">
                      {skill.source_types.map((t) => (
                        <ToolBadge key={t}>{sourceLabel(t)}</ToolBadge>
                      ))}
                    </span>
                    <StatusBadge status={skill.status} />
                    <ArrowRight size={14} className="text-text-dim shrink-0" />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
