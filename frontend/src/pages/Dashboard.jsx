import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSkills } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const DEPARTMENTS = ['Engineering', 'Support', 'Operations', 'Sales', 'HR', 'General'];
const STATUSES = ['all', 'draft', 'review', 'verified', 'outdated'];

function ConfidenceBar({ score }) {
  const pct = Math.round((score ?? 0) * 100);
  let barColor = 'bg-red-500';
  if (score > 0.8) barColor = 'bg-emerald-500';
  else if (score > 0.5) barColor = 'bg-yellow-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-slate-200 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-medium text-slate-500 tabular-nums w-8 text-right">
        {pct}%
      </span>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await getSkills({ limit: 200 });
        const data = res.data;
        if (Array.isArray(data)) {
          setSkills(data);
        } else if (data && Array.isArray(data.items)) {
          setSkills(data.items);
        } else if (data && Array.isArray(data.skills)) {
          setSkills(data.skills);
        } else {
          setSkills([]);
        }
      } catch {
        setError('Failed to load skills.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const filtered = useMemo(() => {
    let result = skills;
    if (statusFilter !== 'all') {
      result = result.filter((s) => s.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((s) => s.name?.toLowerCase().includes(q));
    }
    return result;
  }, [skills, statusFilter, search]);

  const grouped = useMemo(() => {
    const map = {};
    for (const dept of DEPARTMENTS) {
      map[dept] = [];
    }
    for (const skill of filtered) {
      const dept = DEPARTMENTS.includes(skill.department) ? skill.department : 'General';
      map[dept].push(skill);
    }
    return map;
  }, [filtered]);

  const totalSkills = skills.length;
  const verifiedCount = skills.filter((s) => s.status === 'verified').length;
  const avgConfidence =
    skills.length > 0
      ? skills.reduce((sum, s) => sum + (s.confidence ?? 0), 0) / skills.length
      : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div>
      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Company Knowledge Base</h1>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-700 ring-1 ring-inset ring-indigo-200">
            {totalSkills} skills
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-700 ring-1 ring-inset ring-emerald-200">
            {verifiedCount} verified
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700 ring-1 ring-inset ring-slate-200">
            {(avgConfidence * 100).toFixed(0)}% avg confidence
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search skills..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm placeholder:text-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
        />
      </div>

      {/* Skills grouped by department */}
      {filtered.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500">
            {skills.length === 0
              ? 'No skills extracted yet. Start by ingesting documents.'
              : 'No skills match your filters.'}
          </p>
        </div>
      ) : (
        <div className="space-y-10">
          {DEPARTMENTS.map((dept) => {
            const items = grouped[dept];
            if (!items || items.length === 0) return null;
            return (
              <section key={dept}>
                <h2 className="border-l-4 border-indigo-500 pl-3 text-lg font-semibold text-slate-800 mb-4">
                  {dept}{' '}
                  <span className="text-sm font-normal text-slate-400">({items.length})</span>
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((skill) => (
                    <div
                      key={skill.id}
                      onClick={() => navigate(`/skills/${skill.id}`)}
                      className="cursor-pointer rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <h3 className="text-sm font-semibold text-slate-900 truncate">
                          {skill.name}
                        </h3>
                        <StatusBadge status={skill.status} />
                      </div>
                      <ConfidenceBar score={skill.confidence} />
                      <div className="flex items-center gap-3 mt-3 text-xs text-slate-500">
                        {skill.step_count != null && (
                          <span>{skill.step_count} steps</span>
                        )}
                        {skill.needs_review && (
                          <span className="inline-flex items-center gap-1 text-amber-600 font-medium">
                            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                              <path
                                fillRule="evenodd"
                                d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z"
                                clipRule="evenodd"
                              />
                            </svg>
                            Needs review
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
}
