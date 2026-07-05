import { useEffect, useState } from 'react'
import {
  Settings as SettingsIcon, Server, Sparkles, Loader2, CheckCircle2,
  FileText, BrainCircuit, AlertTriangle, Trash2,
} from 'lucide-react'
import { getSkills, getDocuments, runLazyExtraction, deleteWorkspaceData } from '../api/client'
import { Button } from '../components/Primitives'
import Modal from '../components/Modal'
import { useToast } from '../components/Toast'

function InfoRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/60 last:border-0">
      <span className="text-sm text-text-dim">{label}</span>
      <span className="text-sm text-text font-mono">{value}</span>
    </div>
  )
}

function DeleteAllModal({ open, onClose, onDeleted }) {
  const [phrase, setPhrase] = useState('')
  const [deleting, setDeleting] = useState(false)
  const toast = useToast()

  const close = () => {
    if (deleting) return
    setPhrase('')
    onClose()
  }

  const confirm = async () => {
    setDeleting(true)
    try {
      const res = await deleteWorkspaceData()
      const d = res.data?.deleted || {}
      toast(
        `All workspace data deleted: ${d.documents ?? 0} documents, ${d.skills ?? 0} skills, ` +
        `${(d.document_vectors ?? 0) + (d.skill_vectors ?? 0)} vectors. Verified: nothing remains.`,
        'success',
        9000,
      )
      setPhrase('')
      onDeleted()
      onClose()
    } catch (e) {
      toast(e.response?.data?.detail || `Deletion failed: ${e.message}`, 'error', 9000)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Delete all workspace data"
      subtitle="This is irreversible"
    >
      <div className="space-y-4">
        <p className="text-sm text-text-dim leading-relaxed">
          Permanently deletes every document, extracted skill, pending topic,
          feedback entry, connected source (including stored tokens), and all
          vector embeddings. This is a hard delete. Nothing can be recovered.
          API keys are kept.
        </p>
        <div>
          <label className="text-xs font-medium text-text-dim block mb-1.5">
            Type <span className="font-mono text-danger">DELETE</span> to confirm
          </label>
          <input
            className="input-dark font-mono"
            value={phrase}
            onChange={(e) => setPhrase(e.target.value)}
            placeholder="DELETE"
            autoFocus
          />
        </div>
        <Button
          variant="danger"
          className="w-full"
          disabled={phrase !== 'DELETE' || deleting}
          onClick={confirm}
        >
          {deleting
            ? <><Loader2 size={14} className="animate-spin" /> Deleting…</>
            : <><Trash2 size={14} /> Delete everything</>}
        </Button>
      </div>
    </Modal>
  )
}

export default function Settings() {
  const [counts, setCounts] = useState({ skills: null, documents: null })
  const [extracting, setExtracting] = useState(false)
  const [lastRun, setLastRun] = useState(null)
  const [deleteOpen, setDeleteOpen] = useState(false)
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
      const res = await runLazyExtraction()
      const d = res.data || {}
      if ((d.clusters ?? 0) === 0) {
        toast('No document clusters found. Ingest more data first.', 'warning')
        return
      }
      const n = d.skills_extracted ?? 0
      const pending = d.pending_topics ?? 0
      setLastRun({ skills: n, pending, at: new Date() })
      toast(`Extraction complete: ${n} skill${n === 1 ? '' : 's'} ready · ${pending} topic${pending === 1 ? '' : 's'} available on demand.`)
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
          value={counts.documents ?? '-'}
        />
        <InfoRow label="Skills extracted" value={counts.skills ?? '-'} />
      </section>

      {/* Manual extraction */}
      <section className="card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-text flex items-center gap-2">
          <Sparkles size={15} className="text-primary" /> Skill extraction
        </h2>
        <p className="text-sm text-text-dim leading-relaxed">
          Cortex clusters ingested documents by topic, extracts skills from the largest
          clusters right away, and answers the rest on demand at query time. This runs
          automatically after connecting a source. Trigger it manually if you ingested
          data another way or a previous run failed.
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
              {lastRun.skills} skill{lastRun.skills === 1 ? '' : 's'} ready ·{' '}
              {lastRun.pending} topic{lastRun.pending === 1 ? '' : 's'} on demand at{' '}
              {lastRun.at.toLocaleTimeString()}
            </span>
          )}
        </div>
      </section>

      {/* Danger zone */}
      <section className="card p-5 border-danger/40 space-y-3">
        <h2 className="text-sm font-semibold text-danger flex items-center gap-2">
          <AlertTriangle size={15} /> Danger zone
        </h2>
        <p className="text-sm text-text-dim leading-relaxed">
          Permanently delete everything Cortex has ingested and extracted:
          documents, skills, embeddings, and connected-source tokens. Hard
          delete, verified after removal, cannot be undone.
        </p>
        <Button variant="danger" onClick={() => setDeleteOpen(true)}>
          <Trash2 size={14} /> Delete all workspace data
        </Button>
      </section>

      <DeleteAllModal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onDeleted={loadCounts}
      />

      {/* About */}
      <section className="card p-5">
        <h2 className="text-sm font-semibold text-text flex items-center gap-2 mb-2">
          <FileText size={15} className="text-text-dim" /> About
        </h2>
        <p className="text-sm text-text-dim leading-relaxed">
          <span className="font-medium text-text" style={{ letterSpacing: '-0.5px' }}>
            corte<span className="text-primary">x</span>
          </span>{' '}
          turns tribal knowledge
          into AI automation. Connect your team's tools, and Cortex extracts verified,
          executable workflows that both humans and AI agents can follow.
        </p>
      </section>
    </div>
  )
}
