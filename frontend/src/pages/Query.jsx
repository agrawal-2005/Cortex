import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Send, ArrowRight, User, ExternalLink, Sparkles, Plus, X, MessageSquare,
  ChevronDown, ChevronRight, ShieldAlert, UserCheck, Wrench, FileText,
} from 'lucide-react'
import { queryKnowledge, getSkill } from '../api/client'
import SourceIcon from '../components/SourceIcon'
import Logo from '../components/Logo'
import { pct, confidenceColor, formatDate, timeAgo } from '../lib/ui'

// ── Stored chats (localStorage) ───────────────────────────────────────

const CHATS_KEY = 'cortex-chats'
const MAX_CHATS = 20

function loadChats() {
  try {
    const chats = JSON.parse(localStorage.getItem(CHATS_KEY) || '[]')
    return Array.isArray(chats) ? chats : []
  } catch {
    return []
  }
}

function saveChats(chats) {
  try {
    localStorage.setItem(CHATS_KEY, JSON.stringify(chats))
  } catch {
    // Quota exceeded - drop the oldest chats and retry once.
    try {
      localStorage.setItem(CHATS_KEY, JSON.stringify(chats.slice(0, 5)))
    } catch { /* give up silently */ }
  }
}

// A question is a follow-up when it leans on the previous answer for
// context ("what if…", "and…", bare pronouns) rather than naming a topic.
const FOLLOWUP_RE = /^(what if|what about|how about|and |but |also |then |so |why |what's|does (it|that|this)|is (it|that|this)|can (it|we|that))/i

function looksLikeFollowUp(q) {
  return FOLLOWUP_RE.test(q) || (/\b(it|that|this)\b/i.test(q) && q.length < 80)
}

// ── Trust signals ─────────────────────────────────────────────────────

const READINESS_STYLES = {
  executable: 'bg-success/15 text-success border-success/30',
  assisted: 'bg-warning/15 text-warning border-warning/30',
  manual: 'bg-text-dim/15 text-text-dim border-text-dim/30',
}

function ReadinessPill({ readiness }) {
  const level = readiness?.level?.toLowerCase()
  if (!level) return null
  const cls = READINESS_STYLES[level] || READINESS_STYLES.manual
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border capitalize ${cls}`}>
      {level}
    </span>
  )
}

function ConfidenceDot({ value }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-text-dim tabular-nums">
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: confidenceColor(value) }}
        aria-hidden
      />
      {pct(value)} confident
    </span>
  )
}

function JustNowTag() {
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] text-secondary"
      title="Extracted live from your sources for this question"
    >
      <Sparkles size={11} /> Just now
    </span>
  )
}

// ── Callouts (approval gates, failure handling) ───────────────────────

function Callout({ icon: Icon, children }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-warning/25 bg-warning/[0.06] px-3 py-2">
      <Icon size={13} className="text-warning shrink-0 mt-0.5" />
      <p className="text-xs text-text-dim leading-relaxed">{children}</p>
    </div>
  )
}

function normalizeFailures(onFailure) {
  if (!onFailure) return []
  return (Array.isArray(onFailure) ? onFailure : [onFailure])
    .map((r) => (typeof r === 'string' ? { then: r } : r))
    .filter((r) => r && (r.if || r.then))
}

function hasGate(gate) {
  return gate && (gate.if || gate.require)
}

// ── Answer step (numbered list entry) ─────────────────────────────────

function AnswerStep({ step }) {
  const d = step.details || {}
  const gate = hasGate(d.approval_gate) ? d.approval_gate : null
  const failures = normalizeFailures(d.on_failure)
  return (
    <li className="flex gap-3">
      <span className="w-6 h-6 rounded-full bg-surface-2 border border-border text-[11px] font-semibold text-text-dim flex items-center justify-center shrink-0 mt-0.5">
        {step.step_order}
      </span>
      <div className="space-y-1.5 min-w-0 flex-1 pb-1.5">
        <p className="text-sm font-medium text-text">{step.action}</p>
        {d.explanation && (
          <p className="text-sm text-text-dim leading-relaxed">{d.explanation}</p>
        )}
        {d.tool?.name && (
          <p className="text-xs text-text-dim flex items-center gap-1.5 flex-wrap">
            <Wrench size={11} className="text-secondary shrink-0" />
            <span className="text-text font-medium">{d.tool.name}</span>
            {d.tool.method && <span>· {d.tool.method}</span>}
          </p>
        )}
        {d.command && (
          <code className="block text-xs font-mono bg-bg border border-border rounded-md px-2.5 py-1.5 text-secondary overflow-x-auto">
            {d.command}
          </code>
        )}
        {gate && (
          <Callout icon={UserCheck}>
            <span className="font-medium text-warning">Approval required</span>
            {gate.if && <> when <span className="text-text">{gate.if}</span></>}
            {gate.require && <>, sign-off from <span className="text-text">{gate.require}</span></>}
          </Callout>
        )}
        {failures.map((r, i) => (
          <Callout key={i} icon={ShieldAlert}>
            <span className="font-medium text-warning">{r.if ? `If ${r.if}:` : 'On failure:'}</span>{' '}
            {r.then}{r.target && <> → {r.target}</>}
          </Callout>
        ))}
      </div>
    </li>
  )
}

// ── Sources (expandable "N sources" disclosure) ───────────────────────

function collectSources(detail, result) {
  // Prefer the enriched skill detail (real links, authors); dedupe by doc.
  const seen = new Set()
  const out = []
  for (const step of detail?.steps || []) {
    for (const src of step.sources || []) {
      const key = src.document_id || src.snippet
      if (key && seen.has(key)) continue
      if (key) seen.add(key)
      out.push({
        source_type: src.source_type,
        source_link: src.source_link,
        author: src.author_name,
        snippet: src.snippet,
        created_at: src.created_at,
      })
    }
  }
  if (out.length > 0) return out
  return (result.source_hits || []).map((h) => ({
    source_type: h.source_type,
    snippet: h.content_snippet,
    relevance: h.relevance,
  }))
}

function SourceRow({ source }) {
  const inner = (
    <div className="flex items-start gap-2.5 bg-bg border border-border rounded-lg px-3 py-2 hover:border-primary/40 transition-colors">
      <span className="w-6 h-6 rounded-md bg-surface-2 border border-border flex items-center justify-center shrink-0">
        <SourceIcon name={source.source_type} size={12} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[10px] text-text-dim">
          <span className="uppercase tracking-wider font-medium">
            {source.source_type?.replace(/_/g, ' ')}
          </span>
          {source.author && <span>· {source.author}</span>}
          {source.created_at && <span>· {formatDate(source.created_at)}</span>}
          {source.source_link && <ExternalLink size={9} className="text-primary" />}
        </div>
        {source.snippet && (
          <p className="text-xs text-text-dim line-clamp-2 mt-0.5">{source.snippet}</p>
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

// ── Skill answer (prose + steps + trust row) ──────────────────────────

function SkillAnswer({ result, detail, tookMs, condensed }) {
  const skill = result.skill
  const [showSources, setShowSources] = useState(false)
  const [showSteps, setShowSteps] = useState(!condensed)

  const steps = [...(detail?.steps || skill.steps || [])].sort(
    (a, b) => a.step_order - b.step_order,
  )
  const sources = collectSources(detail, result)
  const readiness = detail?.automation_readiness
  const edgeCases = detail?.edge_cases || skill.skill_data?.edge_cases || []
  const conditions = detail?.conditions || skill.skill_data?.conditions || []
  const extractedLive = tookMs > 3000

  return (
    <div className="space-y-3">
      {/* Lead-in prose */}
      {condensed ? (
        <p className="text-sm text-text leading-relaxed">
          Still the{' '}
          <Link to={`/skills/${skill.id}`} className="font-semibold text-primary hover:underline">
            {skill.name}
          </Link>{' '}
          workflow. Here's what applies:
        </p>
      ) : (
        <>
          <p className="text-sm text-text leading-relaxed">
            Here's how this works. It follows the{' '}
            <Link to={`/skills/${skill.id}`} className="font-semibold text-primary hover:underline">
              {skill.name}
            </Link>{' '}
            workflow:
          </p>
          {skill.description && (
            <p className="text-sm text-text-dim leading-relaxed">{skill.description}</p>
          )}
        </>
      )}

      {/* Conditions the workflow applies under (useful for follow-ups) */}
      {condensed && conditions.length > 0 && (
        <p className="text-xs text-text-dim">
          Applies when: {conditions.join('; ')}
        </p>
      )}

      {/* Steps */}
      {steps.length > 0 && (
        condensed && !showSteps ? (
          <button
            onClick={() => setShowSteps(true)}
            className="inline-flex items-center gap-1 text-xs text-text-dim hover:text-text transition-colors"
          >
            <ChevronRight size={12} /> Show the {steps.length} steps again
          </button>
        ) : (
          <ol className="space-y-1 pt-1">
            {steps.map((s) => <AnswerStep key={s.step_order} step={s} />)}
          </ol>
        )
      )}

      {/* Edge cases as callouts */}
      {edgeCases.length > 0 && (
        <div className="space-y-1.5">
          {edgeCases.map((e, i) => (
            <Callout key={i} icon={ShieldAlert}>
              <span className="font-medium text-warning">Watch out:</span>{' '}
              {typeof e === 'string' ? e : JSON.stringify(e)}
            </Callout>
          ))}
        </div>
      )}

      {/* Trust row */}
      <div className="flex items-center gap-3 flex-wrap pt-1 border-t border-border/60 mt-1">
        <ConfidenceDot value={result.confidence ?? skill.confidence} />
        <ReadinessPill readiness={readiness} />
        {sources.length > 0 && (
          <button
            onClick={() => setShowSources((v) => !v)}
            className="inline-flex items-center gap-1 text-[11px] text-text-dim hover:text-text transition-colors"
          >
            <FileText size={11} />
            {sources.length} source{sources.length === 1 ? '' : 's'}
            <ChevronDown size={11} className={`transition-transform ${showSources ? 'rotate-180' : ''}`} />
          </button>
        )}
        {extractedLive && <JustNowTag />}
        <Link
          to={`/skills/${skill.id}`}
          className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline ml-auto"
        >
          View full skill <ArrowRight size={10} />
        </Link>
      </div>

      {showSources && (
        <div className="space-y-1.5">
          {sources.map((s, i) => <SourceRow key={i} source={s} />)}
        </div>
      )}
    </div>
  )
}

// ── Fallback answers ──────────────────────────────────────────────────

function MatchedDocumentsAnswer({ result }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-text leading-relaxed">
        I haven't structured a workflow for this yet, but here's the most
        relevant material I found:
      </p>
      <div className="space-y-1.5">
        {result.matched_documents.map((doc, i) => (
          <SourceRow
            key={i}
            source={{
              source_type: doc.source_type,
              source_link: doc.source_link,
              author: doc.author,
              snippet: doc.preview,
            }}
          />
        ))}
      </div>
      {result.suggestion && (
        <p className="text-xs text-text-dim flex items-start gap-1.5">
          <Sparkles size={12} className="text-primary shrink-0 mt-0.5" />
          <span>
            {result.suggestion}{' '}
            <Link to="/sources" className="text-primary hover:underline">Go to Sources</Link>
          </span>
        </p>
      )}
    </div>
  )
}

function EmptyAnswer() {
  return (
    <p className="text-sm text-text leading-relaxed">
      I don't have knowledge about that yet. Try{' '}
      <Link to="/sources" className="text-primary hover:underline">connecting more sources</Link>
      , or ask about something else.
    </p>
  )
}

function AssistantBody({ message }) {
  if (message.error) {
    return (
      <p className="text-sm text-text-dim leading-relaxed">
        Something went wrong reaching the knowledge base ({message.error}).
        Give it another try in a moment.
      </p>
    )
  }
  const result = message.result
  if (result.skill) {
    return (
      <SkillAnswer
        result={result}
        detail={message.detail}
        tookMs={message.tookMs}
        condensed={message.condensed}
      />
    )
  }
  if (result.matched_documents?.length > 0) {
    return <MatchedDocumentsAnswer result={result} />
  }
  return <EmptyAnswer />
}

// ── Thinking indicator ────────────────────────────────────────────────

function ThinkingIndicator({ stage }) {
  return (
    <div className="flex items-start gap-3">
      <Logo size={26} className="shrink-0 mt-0.5" />
      <div className="flex items-center gap-2.5 pt-1.5">
        <span className="flex items-center gap-1" aria-hidden>
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </span>
        <span className="text-xs text-text-dim">
          {stage === 0
            ? 'Searching your company knowledge…'
            : 'Structuring the answer…'}
        </span>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────

export default function Query() {
  const [chats, setChats] = useState(loadChats)
  const [activeId, setActiveId] = useState(null)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState(0)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const activeChat = chats.find((c) => c.id === activeId)
  const messages = activeChat?.messages || []

  useEffect(() => {
    saveChats(chats)
  }, [chats])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const appendMessage = (chatId, message) => {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? { ...c, messages: [...c.messages, message], updatedAt: Date.now() }
          : c,
      ),
    )
  }

  const startNewChat = () => {
    if (busy) return
    setActiveId(null)
    setInput('')
    textareaRef.current?.focus()
  }

  const deleteChat = (id) => {
    setChats((prev) => prev.filter((c) => c.id !== id))
    if (id === activeId) setActiveId(null)
  }

  const resizeTextarea = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const ask = async (question) => {
    const q = question.trim()
    if (!q || busy) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setBusy(true)
    setStage(0)
    // On-demand extraction takes 5-8s; flip the status once search alone
    // should have finished.
    const stageTimer = setTimeout(() => setStage(1), 2500)

    // First message starts a new stored chat, titled by the question.
    let chatId = activeId
    if (!chatId || !chats.some((c) => c.id === chatId)) {
      chatId = crypto.randomUUID()
      const now = Date.now()
      setChats((prev) => [
        { id: chatId, title: q.slice(0, 80), createdAt: now, updatedAt: now, messages: [] },
        ...prev,
      ].slice(0, MAX_CHATS))
      setActiveId(chatId)
    }
    appendMessage(chatId, { role: 'user', text: q })

    // Follow-ups lean on the previous answer: keep retrieval anchored to
    // the last skill answered in this chat, not treated as a new topic.
    const prevSkill = [...messages].reverse()
      .find((m) => m.role === 'cortex' && m.result?.skill)?.result.skill
    const isFollowUp = prevSkill && looksLikeFollowUp(q)
    const apiQuestion = isFollowUp ? `${q} (regarding: ${prevSkill.name})` : q

    const t0 = Date.now()
    try {
      const res = await queryKnowledge(apiQuestion)
      let detail = null
      if (res.data.skill) {
        // Enrich with automation readiness + linked sources (existing
        // skill-detail endpoint; the query API itself is unchanged).
        try {
          detail = (await getSkill(res.data.skill.id)).data
        } catch {
          detail = null
        }
      }
      appendMessage(chatId, {
        role: 'cortex',
        result: res.data,
        detail,
        tookMs: Date.now() - t0,
        condensed: Boolean(isFollowUp && res.data.skill && res.data.skill.id === prevSkill.id),
      })
    } catch (e) {
      appendMessage(chatId, {
        role: 'cortex',
        error: e.response?.data?.detail || e.message,
      })
    } finally {
      clearTimeout(stageTimer)
      setBusy(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      ask(input)
    }
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">
      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto space-y-6 pr-1 pt-2">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <Logo size={56} className="mb-4" />
              <h2 className="text-base font-semibold text-text">Ask the company brain</h2>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="flex items-start gap-2.5 max-w-[85%]">
                  <div className="bg-primary/20 border border-primary/30 rounded-2xl rounded-tr-md px-4 py-2.5">
                    <p className="text-sm text-text whitespace-pre-wrap">{m.text}</p>
                  </div>
                  <span className="w-7 h-7 rounded-full bg-surface-2 border border-border flex items-center justify-center shrink-0 mt-0.5">
                    <User size={13} className="text-text-dim" />
                  </span>
                </div>
              </div>
            ) : (
              <div key={i} className="flex items-start gap-3 max-w-[92%]">
                <Logo size={26} className="shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <AssistantBody message={m} />
                </div>
              </div>
            ),
          )}
          {busy && <ThinkingIndicator stage={stage} />}
          <div ref={bottomRef} />
        </div>

        {/* Input - pinned to the bottom of the chat column */}
        <form
          className="mt-4 flex items-end gap-2 bg-surface border border-border rounded-2xl px-3 py-2 focus-within:border-primary/50 transition-colors"
          onSubmit={(e) => { e.preventDefault(); ask(input) }}
        >
          <textarea
            ref={textareaRef}
            rows={1}
            className="flex-1 bg-transparent text-sm text-text placeholder:text-text-dim resize-none outline-none py-1.5 max-h-40"
            placeholder="Ask anything…"
            value={input}
            onChange={(e) => { setInput(e.target.value); resizeTextarea() }}
            onKeyDown={onKeyDown}
            disabled={busy}
          />
          <button
            type="submit"
            disabled={!input.trim() || busy}
            className="w-9 h-9 rounded-xl gradient-brand text-white flex items-center justify-center shrink-0 hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Send"
          >
            <Send size={15} />
          </button>
        </form>
      </div>

      {/* Stored chats sidebar */}
      <aside className="w-64 hidden lg:flex flex-col shrink-0 min-h-0">
        <div className="card p-3 flex flex-col min-h-0 max-h-full">
          <button
            onClick={startNewChat}
            disabled={busy}
            className="flex items-center justify-center gap-1.5 w-full px-3 py-2 rounded-lg gradient-brand text-white text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Plus size={15} /> New chat
          </button>
          <h2 className="text-[11px] font-semibold text-text-dim uppercase tracking-wider flex items-center gap-1.5 mt-4 mb-2 px-1">
            <MessageSquare size={11} /> Chats
          </h2>
          {chats.length === 0 ? (
            <p className="text-xs text-text-dim px-1">Your chats will appear here.</p>
          ) : (
            <ul className="space-y-0.5 overflow-y-auto min-h-0 -mx-1 px-1">
              {chats.map((c) => (
                <li key={c.id} className="group relative">
                  <button
                    onClick={() => { if (!busy) setActiveId(c.id) }}
                    className={`w-full text-left rounded-lg px-2.5 py-2 pr-7 transition-colors ${
                      c.id === activeId
                        ? 'bg-surface-2 text-text'
                        : 'text-text-dim hover:text-text hover:bg-surface-2/60'
                    }`}
                  >
                    <p className="text-xs leading-snug truncate">{c.title}</p>
                    <p className="text-[10px] text-text-dim mt-0.5">{timeAgo(c.updatedAt)}</p>
                  </button>
                  <button
                    onClick={() => deleteChat(c.id)}
                    className="absolute right-1.5 top-2 p-1 rounded-md text-text-dim opacity-0 group-hover:opacity-100 hover:text-danger hover:bg-bg transition-all"
                    aria-label="Delete chat"
                    title="Delete chat"
                  >
                    <X size={12} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  )
}
