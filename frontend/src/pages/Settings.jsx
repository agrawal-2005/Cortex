import { useEffect, useState } from 'react'
import {
  Settings as SettingsIcon, Server, Sparkles, Loader2, CheckCircle2,
  FileText, BrainCircuit,
} from 'lucide-react'
import { getSkills, getDocuments, clusterDocuments, extractAllClusters } from '../api/client'
import { Button } from '../components/Primitives'
import { useToast } from '../components/Toast'

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/60 last:border-0">
      <span className="text-sm text-text-dim">{label}</span>
      <span className="text-sm text-text font-mono">{value}</span>
    </div>
  )
}

export default function Settings() {
  const [counts, setCounts] = useState({ skills: null, documents: null })
  const [extracting, setExtracting] = useState(false)
  const [lastRun, setLastRun] = useState(null)
  const toast = useToast()

  const loadCounts = () => {
    getSkills({ limit: 1 })
      .then((res) => setCounts((c) => ({ ...c, skills: res.data.total })))
      .catch(() => {})
    getDocuments({ limit: 100 })
      .then((res) => {
        const d = res.data
        const total = Array.isArray(d) ? d.length : d.total ?? d.items?.length ?? 0
        setCounts((c) => ({ ...c, documents: total }))
      })
      .catch(() => {})
  }

  useEffect(() => { loadCounts() }, [])

  const runExtraction = async () => {
    setExtracting(true)
    try {
      const clusterRes = await clusterDocuments()
      const clusters = clusterRes.data?.clusters || []
      if (clusters.length === 0) {
        toast('No document clusters found — ingest more data first.', 'warning')
        return
      }
      const extractRes = await extractAllClusters(clusters)
      const n = extractRes.data?.skills_extracted ?? 0
      setLastRun({ skills: n, at: new Date() })
      toast(`Extraction complete — ${n} skill${n === 1 ? '' : 's'} extracted.`)
      loadCounts()
    } catch (e) {
      toast(e.response?.data?.detail || 'Skill extraction failed.', 'error')
    } finally {
      setExtracting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <header>
        <h1 className="text-2xl font-bold text-text flex items-center gap-2.5">
          <SettingsIcon size={22} className="text-text-dim" /> Settings
        </h1>
        <p className="text-sm text-text-dim mt-1">Workspace configuration and maintenance.</p>
      </header>

      {/* Backend info */}
      <section className="card p-5">
        <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-2">
          <Server size={15} className="text-secondary" /> Backend
        </h2>
        <InfoRow label="API base" value="/api → localhost:8000" />
        <InfoRow
          label="Documents ingested"
          value={counts.documents ?? '—'}
        />
        <InfoRow label="Skills extracted" value={counts.skills ?? '—'} />
      </section>

      {/* Manual extraction */}
      <section className="card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text flex items-center gap-2">
          <Sparkles size={15} className="text-primary" /> Skill extraction
        </h2>
        <p className="text-sm text-text-dim leading-relaxed">
          Cortex clusters ingested documents by topic and extracts executable skills from
          each cluster. This runs automatically after connecting a source — trigger it
          manually if you ingested data another way or a previous run failed.
        </p>
        <div className="flex items-center gap-3 flex-wrap">
          <Button variant="primary" onClick={runExtraction} disabled={extracting}>
            {extracting
              ? <><Loader2 size={14} className="animate-spin" /> Extracting…</>
              : <><BrainCircuit size={14} /> Run skill extraction</>}
          </Button>
          {lastRun && !extracting && (
            <span className="flex items-center gap-1.5 text-xs text-success">
              <CheckCircle2 size={13} />
              {lastRun.skills} skill{lastRun.skills === 1 ? '' : 's'} extracted at{' '}
              {lastRun.at.toLocaleTimeString()}
            </span>
          )}
        </div>
      </section>

      {/* About */}
      <section className="card p-5">
        <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-2">
          <FileText size={15} className="text-text-dim" /> About
        </h2>
        <p className="text-sm text-text-dim leading-relaxed">
          <span className="gradient-text font-semibold">Cortex</span> turns tribal knowledge
          into AI automation. Connect your team's tools, and Cortex extracts verified,
          executable workflows that both humans and AI agents can follow.
        </p>
      </section>
    </div>
  )
}
