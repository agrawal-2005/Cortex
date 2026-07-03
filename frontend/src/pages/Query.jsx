import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Send, Search, History, Loader2, ArrowRight, User, BrainCircuit } from 'lucide-react'
import { queryKnowledge } from '../api/client'
import { StatusBadge, DeptBadge, ConfidenceBar, Button } from '../components/Primitives'
import SourceIcon from '../components/SourceIcon'
import { pct, confidenceColor } from '../lib/ui'

const RECENT_KEY = 'cortex-recent-queries'

function loadRecent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]')
  } catch {
    return []
  }
}

function SkillResult({ result }) {
  const { skill, readable_answer, source_hits, confidence } = result
  if (!skill && !readable_answer && !source_hits?.length) {
    return (
      <p className="text-sm text-text-dim">
        I don't have knowledge about this yet. Try ingesting more data from{' '}
        <Link to="/sources" className="text-primary hover:underline">relevant sources</Link>.
      </p>
    )
  }
  return (
    <div className="space-y-4">
      {skill && (
        <div className="card p-4 bg-bg">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <Link to={`/skills/${skill.id}`} className="text-sm font-semibold text-text hover:text-primary transition-colors">
              {skill.name}
            </Link>
            <div className="flex items-center gap-2">
              <DeptBadge department={skill.department} />
              <StatusBadge status={skill.status} />
            </div>
          </div>
          {skill.description && (
            <p className="text-xs text-text-dim mt-1.5 line-clamp-3">{skill.description}</p>
          )}
          <Link
            to={`/skills/${skill.id}`}
            className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-3"
          >
            View full skill <ArrowRight size={11} />
          </Link>
        </div>
      )}
      {readable_answer && (
        <p className="text-sm text-text leading-relaxed whitespace-pre-wrap">{readable_answer}</p>
      )}
      <div className="flex items-center gap-3">
        <span className="text-[11px] text-text-dim uppercase tracking-wider">Confidence</span>
        <span className="text-xs font-semibold" style={{ color: confidenceColor(confidence) }}>
          {pct(confidence)}
        </span>
      </div>
      {source_hits?.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-medium text-text-dim uppercase tracking-wider">Sources</p>
          {source_hits.map((hit, i) => (
            <div key={i} className="flex items-start gap-2.5 bg-bg border border-border rounded-lg px-3 py-2">
              <span className="w-6 h-6 rounded-md bg-surface-2 border border-border flex items-center justify-center shrink-0">
                <SourceIcon name={hit.source_type} size={12} />
              </span>
              <p className="text-xs text-text-dim line-clamp-2 flex-1">{hit.content_snippet}</p>
              <span className="text-[10px] text-text-dim tabular-nums shrink-0">
                {pct(hit.relevance)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Query() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [recent, setRecent] = useState(loadRecent)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const ask = async (question) => {
    const q = question.trim()
    if (!q || busy) return
    setInput('')
    setBusy(true)
    setMessages((prev) => [...prev, { role: 'user', text: q }])
    const nextRecent = [q, ...recent.filter((r) => r !== q)].slice(0, 8)
    setRecent(nextRecent)
    localStorage.setItem(RECENT_KEY, JSON.stringify(nextRecent))
    try {
      const res = await queryKnowledge(q)
      setMessages((prev) => [...prev, { role: 'cortex', result: res.data }])
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: 'cortex', error: e.response?.data?.detail || e.message },
      ])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex gap-6 h-[calc(100vh-8rem)]">
      {/* Chat column */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="mb-4">
          <h1 className="text-2xl font-bold text-text">Query</h1>
          <p className="text-sm text-text-dim mt-1">Ask about any company process.</p>
        </header>

        <div className="flex-1 overflow-y-auto space-y-5 pr-1">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-14 h-14 rounded-2xl gradient-brand flex items-center justify-center mb-4 shadow-lg shadow-primary/30">
                <Search size={24} className="text-white" />
              </div>
              <h2 className="text-base font-semibold text-text">Ask the company brain</h2>
              <p className="text-sm text-text-dim mt-1.5 max-w-sm">
                "How do we handle refunds over $500?" · "What's the deploy rollback process?"
              </p>
            </div>
          )}
          {messages.map((m, i) =>
            m.role === 'user' ? (
              <div key={i} className="flex justify-end">
                <div className="flex items-start gap-2.5 max-w-[85%]">
                  <div className="bg-primary/20 border border-primary/30 rounded-2xl rounded-tr-md px-4 py-2.5">
                    <p className="text-sm text-text">{m.text}</p>
                  </div>
                  <span className="w-7 h-7 rounded-full bg-surface-2 border border-border flex items-center justify-center shrink-0 mt-0.5">
                    <User size={13} className="text-text-dim" />
                  </span>
                </div>
              </div>
            ) : (
              <div key={i} className="flex items-start gap-2.5 max-w-[92%]">
                <span className="w-7 h-7 rounded-full gradient-brand flex items-center justify-center shrink-0 mt-0.5">
                  <BrainCircuit size={13} className="text-white" />
                </span>
                <div className="card rounded-2xl rounded-tl-md px-4 py-3.5 flex-1">
                  {m.error ? (
                    <p className="text-sm text-danger">{m.error}</p>
                  ) : (
                    <SkillResult result={m.result} />
                  )}
                </div>
              </div>
            ),
          )}
          {busy && (
            <div className="flex items-center gap-2.5">
              <span className="w-7 h-7 rounded-full gradient-brand flex items-center justify-center">
                <BrainCircuit size={13} className="text-white" />
              </span>
              <Loader2 size={15} className="text-primary animate-spin" />
              <span className="text-xs text-text-dim">Searching company knowledge…</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => { e.preventDefault(); ask(input) }}
        >
          <input
            className="input-dark flex-1"
            placeholder="Ask about any company process…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
          />
          <Button variant="primary" type="submit" disabled={!input.trim() || busy}>
            <Send size={15} />
          </Button>
        </form>
      </div>

      {/* Recent queries sidebar */}
      <aside className="w-60 hidden lg:block shrink-0">
        <div className="card p-4 sticky top-8">
          <h2 className="text-xs font-semibold text-text-dim uppercase tracking-wider flex items-center gap-1.5 mb-3">
            <History size={12} /> Recent queries
          </h2>
          {recent.length === 0 ? (
            <p className="text-xs text-text-dim">Your queries will appear here.</p>
          ) : (
            <ul className="space-y-1">
              {recent.map((q) => (
                <li key={q}>
                  <button
                    onClick={() => ask(q)}
                    className="w-full text-left text-xs text-text-dim hover:text-text hover:bg-surface-2 rounded-md px-2 py-1.5 transition-colors line-clamp-2"
                  >
                    {q}
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
