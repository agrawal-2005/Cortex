import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ClipboardList, FileText, Plug, Gauge, ArrowRight,
  Sparkles, Inbox, AlertTriangle,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { getSkills, getDocuments, getDocumentSourceTypes, getSkillStats } from '../api/client'
import { Skeleton, SkeletonCard, EmptyState, StatusBadge, ConfidenceBar, Button } from '../components/Primitives'
import SourceIcon from '../components/SourceIcon'
import { confidenceColor, pct, timeAgo, sourceKeyOf } from '../lib/ui'

const DEPT_COLORS = ['#6C5CE7', '#00D2FF', '#00E676', '#FFB300', '#FF79C6', '#8888A0']

function StatCard({ icon: Icon, label, value, sub, accent = 'text-primary' }) {
  return (
    <div className="card card-hover p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-text-dim uppercase tracking-wider">{label}</p>
        <Icon size={16} className={accent} />
      </div>
      <p className="text-3xl font-bold text-text mt-2 tabular-nums">{value}</p>
      <div className="text-xs text-text-dim mt-1.5">{sub}</div>
    </div>
  )
}

export default function Dashboard() {
  const [skills, setSkills] = useState(null)
  const [documents, setDocuments] = useState(null)
  const [sourceTypes, setSourceTypes] = useState(null)
  const [skillStats, setSkillStats] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      getSkills({ limit: 100 }),
      getDocuments({ limit: 100 }),
      getDocumentSourceTypes(),
    ])
      .then(([skillsRes, docsRes, typesRes]) => {
        setSkills(skillsRes.data.items || skillsRes.data.skills || [])
        setDocuments(Array.isArray(docsRes.data) ? docsRes.data : docsRes.data.items || [])
        setSourceTypes(Array.isArray(typesRes.data) ? typesRes.data : [])
      })
      .catch((e) => setError(e.message))
    getSkillStats()
      .then((res) => setSkillStats(res.data))
      .catch(() => {})
  }, [])

  const stats = useMemo(() => {
    if (!skills || !documents || !sourceTypes) return null
    const verified = skills.filter((s) => s.status === 'verified').length
    const inReview = skills.filter((s) => s.status === 'review' || s.status === 'draft').length
    const avgConf = skills.length
      ? skills.reduce((acc, s) => acc + (s.confidence || 0), 0) / skills.length
      : 0
    // Dedupe github_issue / github_pr / github_doc etc. down to one source key
    // (same sourceKeyOf as the Data Sources page, so both pages agree)
    const sourceKeys = [...new Set(sourceTypes.map(sourceKeyOf).filter(Boolean))]
    const byDept = {}
    for (const s of skills) {
      const dept = s.department || 'general'
      byDept[dept] = (byDept[dept] || 0) + 1
    }
    const deptData = Object.entries(byDept)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
    return { verified, inReview, avgConf, sourceKeys, deptData }
  }, [skills, documents, sourceTypes])

  const needsReview = useMemo(
    () =>
      (skills || [])
        .filter((s) => s.status === 'draft' || s.status === 'review')
        .sort((a, b) => (a.confidence || 0) - (b.confidence || 0))
        .slice(0, 4),
    [skills],
  )

  const activity = useMemo(() => {
    if (!skills || !documents) return []
    const items = [
      ...skills.map((s) => ({
        key: `skill-${s.id}`,
        icon: Sparkles,
        text: `Skill extracted: ${s.name}`,
        time: s.extracted_at,
        link: `/skills/${s.id}`,
      })),
      ...documents.slice(0, 20).map((d) => ({
        key: `doc-${d.id}`,
        sourceType: d.source_type,
        text: `Ingested from ${d.channel_or_project || d.source_type}${d.author_name ? ` · ${d.author_name}` : ''}`,
        time: d.ingested_at,
      })),
    ]
    return items
      .filter((i) => i.time)
      .sort((a, b) => new Date(b.time) - new Date(a.time))
      .slice(0, 8)
  }, [skills, documents])

  if (error) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Could not load dashboard"
        message={`The API returned an error: ${error}. Is the backend running on port 8000?`}
      />
    )
  }

  const loading = !stats

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-text">Dashboard</h1>
        <p className="text-sm text-text-dim mt-1">
          Extract how your company actually works. Turn it into workflows AI agents can run.
        </p>
      </header>

      {/* Stats row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} lines={2} />)
        ) : (
          <>
            <StatCard
              icon={ClipboardList}
              label="Total Skills"
              value={skillStats?.skills_ready ?? skills.length}
              sub={
                skillStats ? (
                  <span>
                    <span className="text-success">{skillStats.skills_ready} ready</span>
                    {' · '}
                    <span className="text-secondary">
                      {skillStats.topics_on_demand} topic{skillStats.topics_on_demand === 1 ? '' : 's'} on demand
                    </span>
                  </span>
                ) : (
                  <span>
                    <span className="text-success">{stats.verified} verified</span>
                    {' · '}
                    <span className="text-warning">{stats.inReview} in review</span>
                  </span>
                )
              }
            />
            <StatCard
              icon={FileText}
              label="Documents Ingested"
              value={documents.length >= 100 ? '100+' : documents.length}
              sub="across all sources"
              accent="text-secondary"
            />
            <StatCard
              icon={Plug}
              label="Data Sources"
              value={stats.sourceKeys.length}
              sub={
                stats.sourceKeys.length ? (
                  <span className="flex items-center gap-1.5 mt-0.5">
                    {stats.sourceKeys.slice(0, 5).map((t) => (
                      <SourceIcon key={t} name={t} size={13} />
                    ))}
                    <span>connected</span>
                  </span>
                ) : (
                  'none connected yet'
                )
              }
              accent="text-success"
            />
            <StatCard
              icon={Gauge}
              label="Avg Confidence"
              value={
                <span style={{ color: confidenceColor(stats.avgConf) }}>
                  {pct(stats.avgConf)}
                </span>
              }
              sub="across all skills"
              accent="text-warning"
            />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Skills by department */}
        <section className="card p-5 lg:col-span-3">
          <h2 className="text-sm font-semibold text-text mb-4">Skills by Department</h2>
          {loading ? (
            <Skeleton className="h-48 w-full" />
          ) : stats.deptData.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="No skills yet"
              message="Connect a data source and Cortex will start extracting skills."
              action={
                <Link to="/sources">
                  <Button variant="primary">Connect a source <ArrowRight size={14} /></Button>
                </Link>
              }
            />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(160, stats.deptData.length * 44)}>
              <BarChart data={stats.deptData} layout="vertical" margin={{ left: 8, right: 24 }}>
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  tick={{ fill: '#8888A0', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: '#1E1E2E55' }}
                  contentStyle={{
                    background: '#12121A',
                    border: '1px solid #1E1E2E',
                    borderRadius: 8,
                    color: '#E8E8ED',
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={18}>
                  {stats.deptData.map((_, i) => (
                    <Cell key={i} fill={DEPT_COLORS[i % DEPT_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        {/* Recent activity */}
        <section className="card p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-text mb-4">Recent Activity</h2>
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
            </div>
          ) : activity.length === 0 ? (
            <p className="text-sm text-text-dim py-6 text-center">
              No activity yet. Ingest some data to get started.
            </p>
          ) : (
            <ul className="space-y-1">
              {activity.map((item) => {
                const Icon = item.icon
                const row = (
                  <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-surface-2 transition-colors">
                    <span className="w-7 h-7 rounded-lg bg-bg border border-border flex items-center justify-center shrink-0">
                      {Icon ? <Icon size={13} className="text-primary" /> : <SourceIcon name={item.sourceType} size={13} />}
                    </span>
                    <span className="text-[13px] text-text truncate flex-1">{item.text}</span>
                    <span className="text-[11px] text-text-dim shrink-0">{timeAgo(item.time)}</span>
                  </div>
                )
                return (
                  <li key={item.key}>
                    {item.link ? <Link to={item.link}>{row}</Link> : row}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>

      {/* Skills needing review */}
      {!loading && needsReview.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-text flex items-center gap-2">
              <AlertTriangle size={15} className="text-warning" />
              Skills Needing Review
            </h2>
            <Link to="/review" className="text-xs text-primary hover:underline flex items-center gap-1">
              Open review queue <ArrowRight size={12} />
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {needsReview.map((s) => (
              <Link
                key={s.id}
                to={`/skills/${s.id}`}
                className="card card-hover p-4 border-warning/25 bg-warning/[0.03]"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-text line-clamp-2">{s.name}</p>
                  <StatusBadge status={s.status} />
                </div>
                <ConfidenceBar value={s.confidence} className="mt-3" />
              </Link>
            ))}
          </div>
        </section>
      )}

      {!loading && skills.length === 0 && documents.length === 0 && (
        <EmptyState
          icon={Inbox}
          title="Welcome to Cortex"
          message="Connect your first data source — Slack, GitHub, or Discord — and Cortex will extract your team's tribal knowledge into executable skills."
          action={
            <Link to="/sources">
              <Button variant="primary">Connect a data source <ArrowRight size={14} /></Button>
            </Link>
          }
        />
      )}
    </div>
  )
}
