import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Loader2, Terminal } from 'lucide-react'
import {
  getDocuments, uploadSlackExport, uploadFile, ingestGitHub,
  uploadDiscordExport, ingestDiscordLive, clusterDocuments, extractAllClusters,
  getIngestStatus,
} from '../api/client'
import Modal from '../components/Modal'
import DropZone from '../components/DropZone'
import SourceIcon from '../components/SourceIcon'
import { Button } from '../components/Primitives'
import { useToast } from '../components/Toast'

const INTEGRATIONS = [
  { key: 'slack', name: 'Slack', description: 'Team conversations', availability: 'available' },
  { key: 'jira', name: 'Jira', description: 'Issue tracking', availability: 'available' },
  { key: 'github', name: 'GitHub', description: 'Code & PRs', availability: 'available' },
  { key: 'discord', name: 'Discord', description: 'Community chat', availability: 'available' },
  { key: 'notion', name: 'Notion', description: 'Documentation', availability: 'coming_soon' },
  { key: 'confluence', name: 'Confluence', description: 'Wiki & docs', availability: 'coming_soon' },
  { key: 'gmail', name: 'Gmail', description: 'Email threads', availability: 'coming_soon' },
  { key: 'teams', name: 'MS Teams', description: 'Team chat', availability: 'coming_soon' },
  { key: 'linear', name: 'Linear', description: 'Issue tracking', availability: 'coming_soon' },
  { key: 'api', name: 'Custom API', description: 'Any REST API', availability: 'available' },
  { key: 'file', name: 'File Upload', description: 'CSV, JSON, PDF', availability: 'available' },
  { key: 'database', name: 'Database', description: 'Direct connect', availability: 'coming_soon' },
]

const ACTIVE_INGEST_KEY = 'cortex-active-ingest'

// Poll a background ingest task until it completes or fails.
async function pollIngestTask(taskId, onProgress) {
  for (;;) {
    await new Promise((r) => setTimeout(r, 2000))
    const res = await getIngestStatus(taskId)
    const task = res.data
    if (task.status === 'completed' || task.status === 'failed') return task
    onProgress?.(task)
  }
}

// Map document source_type prefixes to integration keys
function sourceKeyOf(sourceType) {
  if (!sourceType) return null
  if (sourceType.startsWith('github')) return 'github'
  if (sourceType === 'slack') return 'slack'
  if (sourceType === 'discord') return 'discord'
  if (sourceType === 'jira') return 'jira'
  return 'file'
}

// ── Integration card ──────────────────────────────────────────────────

function IntegrationCard({ integration, connected, onConnect }) {
  const { key, name, description, availability } = integration
  const comingSoon = availability === 'coming_soon'
  return (
    <div className={`card card-hover p-5 flex flex-col relative group ${comingSoon ? 'opacity-70' : ''}`}>
      <div className="flex items-center justify-between">
        <div className="w-10 h-10 rounded-xl bg-bg border border-border flex items-center justify-center">
          <SourceIcon name={key} size={20} />
        </div>
        {connected ? (
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-success">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Connected
          </span>
        ) : (
          <span className="text-[11px] text-text-dim">
            {comingSoon ? '○ Coming soon' : '○ Available'}
          </span>
        )}
      </div>
      <h3 className="text-sm font-semibold text-text mt-3">{name}</h3>
      <p className="text-xs text-text-dim mt-0.5 mb-4">{description}</p>
      <div className="mt-auto">
        {comingSoon ? (
          <>
            <Button className="w-full" disabled>Coming soon</Button>
            <div className="absolute left-1/2 -translate-x-1/2 bottom-16 hidden group-hover:block z-10 w-56 glass rounded-lg px-3 py-2 text-[11px] text-text-dim text-center shadow-xl">
              This integration is coming soon. Want it sooner? Let us know.
            </div>
          </>
        ) : (
          <Button
            variant={connected ? 'default' : 'primary'}
            className="w-full"
            onClick={() => onConnect(key)}
          >
            {connected ? (key === 'file' ? 'Upload more' : 'Sync again') : key === 'file' ? 'Upload' : 'Connect'}
          </Button>
        )}
      </div>
    </div>
  )
}

// ── Progress panel ────────────────────────────────────────────────────

function ProgressPanel({ progress }) {
  if (!progress) return null
  const { stage, label, skills } = progress
  return (
    <div className="card p-5 border-primary/30">
      {stage === 'done' ? (
        <div className="flex items-center gap-3">
          <CheckCircle2 size={18} className="text-success shrink-0" />
          <p className="text-sm text-text flex-1">
            {label}
            {skills != null && (
              <> <span className="text-success font-medium">{skills} skills extracted.</span></>
            )}
          </p>
          <Link to="/" className="text-sm text-primary hover:underline flex items-center gap-1 shrink-0">
            View dashboard <ArrowRight size={13} />
          </Link>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-3">
            <Loader2 size={16} className="text-primary animate-spin shrink-0" />
            <p className="text-sm text-text">{label}</p>
          </div>
          <div className="h-1.5 mt-3 rounded-full bg-border overflow-hidden">
            <div className="h-full w-1/3 gradient-brand rounded-full animate-[progress-slide_1.2s_ease-in-out_infinite]" />
          </div>
          <style>{`@keyframes progress-slide { 0% { margin-left: -33%; } 100% { margin-left: 100%; } }`}</style>
        </>
      )}
    </div>
  )
}

// ── Connect modals ────────────────────────────────────────────────────

function SlackModal({ open, onClose, onIngest }) {
  const [tab, setTab] = useState('export')
  const [token, setToken] = useState('')
  const [file, setFile] = useState(null)
  const toast = useToast()
  return (
    <Modal open={open} onClose={onClose} title="Connect Slack" subtitle="Ingest team conversations into Cortex">
      <div className="flex gap-1 mb-4 bg-bg rounded-lg p-1 border border-border">
        {[['export', 'Upload Export'], ['token', 'Bot Token']].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`flex-1 text-sm py-1.5 rounded-md transition-colors ${tab === k ? 'bg-surface-2 text-text font-medium' : 'text-text-dim hover:text-text'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'export' ? (
        <div className="space-y-4">
          <DropZone accept=".zip" hint="Slack export .zip archive" file={file} onFile={setFile} />
          <Button
            variant="primary"
            className="w-full"
            disabled={!file}
            onClick={() => onIngest('Slack', () => uploadSlackExport(file))}
          >
            Ingest export
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim block mb-1.5">Slack Bot Token</label>
            <input
              className="input-dark font-mono"
              type="password"
              placeholder="xoxb-…"
              value={token}
              onChange={(e) => setToken(e.target.value)}
            />
          </div>
          <Button
            variant="primary"
            className="w-full"
            disabled={!token}
            onClick={() => toast('Live Slack sync is coming soon — upload an export .zip for now.', 'info')}
          >
            Connect
          </Button>
        </div>
      )}
    </Modal>
  )
}

function GitHubModal({ open, onClose, onIngest }) {
  const [repo, setRepo] = useState('')
  const [token, setToken] = useState('')
  const valid = /^[\w.-]+\/[\w.-]+$/.test(repo.trim())
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Connect GitHub"
      subtitle="Pulls issues, PRs, discussions, and docs from the last 6 months"
    >
      <div className="space-y-4">
        <div>
          <label className="text-xs font-medium text-text-dim block mb-1.5">Repository</label>
          <input
            className="input-dark font-mono"
            placeholder="owner/repo — e.g. usestrix/strix"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs font-medium text-text-dim block mb-1.5">
            GitHub Token <span className="font-normal">(optional, for private repos &amp; higher rate limits)</span>
          </label>
          <input
            className="input-dark font-mono"
            type="password"
            placeholder="ghp_…"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
        </div>
        <Button
          variant="primary"
          className="w-full"
          disabled={!valid}
          onClick={() => onIngest(repo.trim(), () => ingestGitHub({ repo: repo.trim(), token: token.trim() }))}
        >
          Ingest repository
        </Button>
      </div>
    </Modal>
  )
}

function DiscordModal({ open, onClose, onIngest }) {
  const [tab, setTab] = useState('export')
  const [file, setFile] = useState(null)
  const [botToken, setBotToken] = useState('')
  const [guildId, setGuildId] = useState('')
  const [channelIds, setChannelIds] = useState('')
  const liveValid = botToken && guildId && channelIds.trim()
  return (
    <Modal open={open} onClose={onClose} title="Connect Discord" subtitle="Ingest community conversations">
      <div className="flex gap-1 mb-4 bg-bg rounded-lg p-1 border border-border">
        {[['export', 'Upload Export'], ['token', 'Bot Token']].map(([k, label]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`flex-1 text-sm py-1.5 rounded-md transition-colors ${tab === k ? 'bg-surface-2 text-text font-medium' : 'text-text-dim hover:text-text'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'export' ? (
        <div className="space-y-4">
          <DropZone
            accept=".json"
            hint="DiscordChatExporter .json export"
            file={file}
            onFile={setFile}
          />
          <p className="text-[11px] text-text-dim">
            Export channels with{' '}
            <a
              href="https://github.com/Tyrrrz/DiscordChatExporter"
              target="_blank"
              rel="noreferrer"
              className="text-primary hover:underline"
            >
              DiscordChatExporter
            </a>{' '}
            in JSON format.
          </p>
          <Button
            variant="primary"
            className="w-full"
            disabled={!file}
            onClick={() => onIngest('Discord export', () => uploadDiscordExport(file))}
          >
            Ingest export
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-text-dim block mb-1.5">Bot Token</label>
            <input
              className="input-dark font-mono"
              type="password"
              value={botToken}
              onChange={(e) => setBotToken(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-text-dim block mb-1.5">Guild (Server) ID</label>
            <input className="input-dark font-mono" value={guildId} onChange={(e) => setGuildId(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-text-dim block mb-1.5">
              Channel IDs <span className="font-normal">(comma-separated)</span>
            </label>
            <input className="input-dark font-mono" value={channelIds} onChange={(e) => setChannelIds(e.target.value)} />
          </div>
          <Button
            variant="primary"
            className="w-full"
            disabled={!liveValid}
            onClick={() =>
              onIngest('Discord', () =>
                ingestDiscordLive({
                  botToken: botToken.trim(),
                  guildId: guildId.trim(),
                  channelIds: channelIds.split(',').map((c) => c.trim()).filter(Boolean),
                }),
              )
            }
          >
            Connect &amp; ingest
          </Button>
        </div>
      )}
    </Modal>
  )
}

function FileModal({ open, onClose, onIngest, sourceType = 'custom', title = 'Upload File' }) {
  const [file, setFile] = useState(null)
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      subtitle="Each record needs a `content` field"
    >
      <div className="space-y-4">
        <DropZone accept=".csv,.json" hint="CSV or JSON (PDF coming soon)" file={file} onFile={setFile} />
        <Button
          variant="primary"
          className="w-full"
          disabled={!file}
          onClick={() => onIngest(file.name, () => uploadFile(file, sourceType))}
        >
          Ingest file
        </Button>
      </div>
    </Modal>
  )
}

function ApiModal({ open, onClose }) {
  const snippet = `curl -X POST http://localhost:8000/api/v1/ingest/batch \\
  -H "Content-Type: application/json" \\
  -d '[{
    "content": "How we handle refunds over $500…",
    "source_type": "custom_api",
    "source_id": "kb-123",
    "author_name": "Sarah Chen",
    "channel_or_project": "support-kb"
  }]'`
  return (
    <Modal open={open} onClose={onClose} title="Custom API" subtitle="Push documents from any system" wide>
      <p className="text-sm text-text-dim mb-3">
        POST document batches directly to the Cortex ingestion API:
      </p>
      <pre className="bg-bg border border-border rounded-lg p-4 text-xs font-mono text-text overflow-x-auto flex gap-2">
        <Terminal size={14} className="text-text-dim shrink-0 mt-0.5" />
        <code>{snippet}</code>
      </pre>
    </Modal>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function Sources() {
  const [connectedKeys, setConnectedKeys] = useState(new Set())
  const [activeModal, setActiveModal] = useState(null)
  const [progress, setProgress] = useState(null)
  const toast = useToast()

  const refreshConnected = useCallback(() => {
    getDocuments({ limit: 100 })
      .then((res) => {
        const docs = Array.isArray(res.data) ? res.data : res.data.items || []
        setConnectedKeys(new Set(docs.map((d) => sourceKeyOf(d.source_type)).filter(Boolean)))
      })
      .catch(() => {})
  }, [])

  useEffect(() => { refreshConnected() }, [refreshConnected])

  // After ingestion: refresh badges, then run clustering + skill extraction.
  const finishIngest = useCallback(async (label, count, stats) => {
    if (stats?.rate_limited) {
      toast(
        'Rate limit hit — this was a partial sync. Add an access token and sync again to fetch everything.',
        'warning',
        8000,
      )
    }
    refreshConnected()
    toast(`${count} documents ingested from ${label}.`)
    setProgress({ stage: 'extracting', label: `✅ ${count} documents ingested. Extracting skills…` })
    try {
      const clusterRes = await clusterDocuments()
      const clusters = clusterRes.data?.clusters || []
      let skillCount = 0
      if (clusters.length) {
        const extractRes = await extractAllClusters(clusters)
        skillCount = extractRes.data?.skills_extracted ?? 0
      }
      setProgress({ stage: 'done', label: `✅ ${count} documents ingested. `, skills: skillCount })
      if (skillCount) toast(`${skillCount} skills extracted.`)
    } catch {
      setProgress({ stage: 'done', label: `✅ ${count} documents ingested.` })
      toast('Skill extraction could not run automatically — trigger it from Settings.', 'warning', 6000)
    }
  }, [refreshConnected, toast])

  // Wait for a background ingest task, surviving page reloads via localStorage.
  const trackIngestTask = useCallback(async (taskId, label) => {
    localStorage.setItem(ACTIVE_INGEST_KEY, JSON.stringify({ taskId, label }))
    setProgress({ stage: 'ingesting', label: `Ingesting documents from ${label}… (safe to leave this page)` })
    let task
    try {
      task = await pollIngestTask(taskId, (t) => {
        const stage = t.progress?.stage
        setProgress({
          stage: 'ingesting',
          label: `Ingesting documents from ${label}${stage ? ` — ${stage}` : ''}… (safe to leave this page)`,
        })
      })
    } catch (e) {
      localStorage.removeItem(ACTIVE_INGEST_KEY)
      setProgress(null)
      if (e.response?.status === 404) {
        toast('The backend was restarted — that sync is no longer tracked. Please sync again.', 'warning', 7000)
      } else {
        toast(`Lost track of the ${label} sync: ${e.message}`, 'error', 7000)
      }
      return
    }
    localStorage.removeItem(ACTIVE_INGEST_KEY)
    if (task.status === 'failed') {
      setProgress(null)
      toast(task.error || `Ingestion from ${label} failed.`, 'error', 7000)
      return
    }
    const p = task.progress || {}
    await finishIngest(label, p.documents_ingested ?? p.documents_created ?? 0, p.stats)
  }, [finishIngest, toast])

  // Shared ingest flow: run the request, then trigger skill extraction.
  const runIngest = useCallback(async (label, request) => {
    setActiveModal(null)
    setProgress({ stage: 'ingesting', label: `Ingesting documents from ${label}…` })
    let d
    try {
      const res = await request()
      d = res.data || {}
    } catch (e) {
      setProgress(null)
      toast(e.response?.data?.detail || `Ingestion from ${label} failed: ${e.message}`, 'error', 7000)
      return
    }
    // Background task (202): poll for completion instead of reading the body.
    if (d.task_id && (d.status === 'running' || d.status === 'pending')) {
      await trackIngestTask(d.task_id, label)
      return
    }
    if (d.status === 'failed') {
      setProgress(null)
      toast(d.error || `Ingestion from ${label} failed.`, 'error', 7000)
      return
    }
    const count = d.documents_ingested ?? d.documents_created
      ?? d.progress?.documents_ingested ?? d.progress?.documents_created ?? 0
    await finishIngest(label, count, d.stats ?? d.progress?.stats)
  }, [finishIngest, trackIngestTask, toast])

  // On mount: resume tracking an ingest that was running before a reload.
  useEffect(() => {
    const raw = localStorage.getItem(ACTIVE_INGEST_KEY)
    if (!raw) return
    let saved
    try {
      saved = JSON.parse(raw)
    } catch {
      localStorage.removeItem(ACTIVE_INGEST_KEY)
      return
    }
    if (saved?.taskId) trackIngestTask(saved.taskId, saved.label || 'source')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const sections = useMemo(() => {
    const connected = INTEGRATIONS.filter((i) => connectedKeys.has(i.key))
    const available = INTEGRATIONS.filter((i) => !connectedKeys.has(i.key))
    return { connected, available }
  }, [connectedKeys])

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-text">Data Sources</h1>
        <p className="text-sm text-text-dim mt-1">
          Connect the tools where your team's knowledge lives.
        </p>
      </header>

      <ProgressPanel progress={progress} />

      {sections.connected.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-success" /> Connected
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sections.connected.map((integration) => (
              <IntegrationCard
                key={integration.key}
                integration={integration}
                connected
                onConnect={setActiveModal}
              />
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-xs font-semibold text-text-dim uppercase tracking-wider mb-3">
          Available
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.available.map((integration) => (
            <IntegrationCard
              key={integration.key}
              integration={integration}
              connected={false}
              onConnect={setActiveModal}
            />
          ))}
        </div>
      </section>

      {/* Modals */}
      <SlackModal open={activeModal === 'slack'} onClose={() => setActiveModal(null)} onIngest={runIngest} />
      <GitHubModal open={activeModal === 'github'} onClose={() => setActiveModal(null)} onIngest={runIngest} />
      <DiscordModal open={activeModal === 'discord'} onClose={() => setActiveModal(null)} onIngest={runIngest} />
      <FileModal open={activeModal === 'file'} onClose={() => setActiveModal(null)} onIngest={runIngest} />
      <FileModal
        open={activeModal === 'jira'}
        onClose={() => setActiveModal(null)}
        onIngest={runIngest}
        sourceType="jira"
        title="Connect Jira — upload export"
      />
      <ApiModal open={activeModal === 'api'} onClose={() => setActiveModal(null)} />
    </div>
  )
}
