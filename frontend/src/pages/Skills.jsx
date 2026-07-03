import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  LayoutGrid, List, Search, ClipboardList, Layers, Quote, Clock,
} from 'lucide-react'
import { getSkills } from '../api/client'
import {
  StatusBadge, DeptBadge, ConfidenceBar, SkeletonCard, EmptyState, Button,
} from '../components/Primitives'
import { timeAgo } from '../lib/ui'

const STATUSES = ['all', 'verified', 'review', 'draft', 'outdated']
const CONFIDENCE_RANGES = [
  { label: 'Any confidence', min: 0 },
  { label: '≥ 50%', min: 0.5 },
  { label: '≥ 75%', min: 0.75 },
  { label: '≥ 90%', min: 0.9 },
]

function SkillCard({ skill, view }) {
  const meta = (
    <div className="flex items-center gap-4 text-[11px] text-text-dim">
      <span className="flex items-center gap-1"><Layers size={11} /> {skill.step_count} steps</span>
      <span className="flex items-center gap-1"><Quote size={11} /> {skill.source_count ?? 0} sources</span>
      <span className="flex items-center gap-1"><Clock size={11} /> {timeAgo(skill.extracted_at)}</span>
    </div>
  )
  if (view === 'list') {
    return (
      <Link to={`/skills/${skill.id}`} className="card card-hover px-5 py-4 flex items-center gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text truncate">{skill.name}</p>
          <div className="mt-1.5">{meta}</div>
        </div>
        <DeptBadge department={skill.department} />
        <StatusBadge status={skill.status} />
        <div className="w-36 hidden sm:block">
          <ConfidenceBar value={skill.confidence} />
        </div>
      </Link>
    )
  }
  return (
    <Link to={`/skills/${skill.id}`} className="card card-hover p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-text line-clamp-2">{skill.name}</p>
        <StatusBadge status={skill.status} />
      </div>
      <p className="text-xs text-text-dim line-clamp-2">{skill.description}</p>
      <div className="flex items-center gap-2">
        <DeptBadge department={skill.department} />
      </div>
      <ConfidenceBar value={skill.confidence} />
      {meta}
    </Link>
  )
}

export default function Skills() {
  const [skills, setSkills] = useState(null)
  const [view, setView] = useState('grid')
  const [status, setStatus] = useState('all')
  const [department, setDepartment] = useState('all')
  const [minConf, setMinConf] = useState(0)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const params = { limit: 100 }
    if (status !== 'all') params.status = status
    if (minConf > 0) params.min_confidence = minConf
    if (search.trim()) params.search = search.trim()
    const t = setTimeout(() => {
      getSkills(params)
        .then((res) => setSkills(res.data.items || []))
        .catch(() => setSkills([]))
    }, search ? 250 : 0)
    return () => clearTimeout(t)
  }, [status, minConf, search])

  const departments = useMemo(
    () => [...new Set((skills || []).map((s) => s.department).filter(Boolean))],
    [skills],
  )

  const visible = useMemo(
    () =>
      (skills || []).filter(
        (s) => department === 'all' || s.department === department,
      ),
    [skills, department],
  )

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-text">Skills</h1>
          <p className="text-sm text-text-dim mt-1">
            Executable workflows extracted from your company's knowledge.
          </p>
        </div>
        <div className="flex gap-1 bg-surface border border-border rounded-lg p-1">
          {[['grid', LayoutGrid], ['list', List]].map(([mode, Icon]) => (
            <button
              key={mode}
              onClick={() => setView(mode)}
              aria-label={`${mode} view`}
              className={`p-1.5 rounded-md transition-colors ${view === mode ? 'bg-primary/20 text-primary' : 'text-text-dim hover:text-text'}`}
            >
              <Icon size={15} />
            </button>
          ))}
        </div>
      </header>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-52">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim" />
          <input
            className="input-dark pl-9"
            placeholder="Search skills…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="input-dark w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>{s === 'all' ? 'All statuses' : s}</option>
          ))}
        </select>
        <select className="input-dark w-auto" value={department} onChange={(e) => setDepartment(e.target.value)}>
          <option value="all">All departments</option>
          {departments.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          className="input-dark w-auto"
          value={minConf}
          onChange={(e) => setMinConf(Number(e.target.value))}
        >
          {CONFIDENCE_RANGES.map((r) => (
            <option key={r.min} value={r.min}>{r.label}</option>
          ))}
        </select>
      </div>

      {/* Results */}
      {!skills ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No skills found"
          message={
            search || status !== 'all' || department !== 'all' || minConf > 0
              ? 'No skills match your filters. Try widening the search.'
              : 'Connect a data source and Cortex will extract skills automatically.'
          }
          action={
            !search && (
              <Link to="/sources">
                <Button variant="primary">Connect a source</Button>
              </Link>
            )
          }
        />
      ) : (
        <div className={view === 'grid' ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-2'}>
          {visible.map((s) => <SkillCard key={s.id} skill={s} view={view} />)}
        </div>
      )}
    </div>
  )
}
