import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { queryKnowledge } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ConfidenceBadge from '../components/ConfidenceBadge'
import StatusBadge from '../components/StatusBadge'

const EXAMPLE_QUESTIONS = [
  'How do we handle customer refunds?',
  "What's the deployment process?",
  'How do we onboard new engineers?',
]

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="h-2 w-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  )
}

function SourceCitations({ sources }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3 border-t border-gray-100 pt-2">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs font-medium text-gray-500 hover:text-gray-700 flex items-center gap-1"
      >
        <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>&#9654;</span>
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((src, i) => (
            <div key={i} className="rounded-lg bg-gray-50 p-3 text-xs space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-mono text-gray-500" title={src.document_id}>
                  {src.document_id?.slice(0, 8) || 'doc'}
                </span>
                <StatusBadge status={src.source_type || 'unknown'} />
              </div>
              {src.content_snippet && (
                <p className="text-gray-600 leading-relaxed">{src.content_snippet}</p>
              )}
              {src.relevance != null && (
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">Relevance</span>
                  <div className="flex-1 h-1.5 rounded-full bg-gray-200 overflow-hidden max-w-[120px]">
                    <div
                      className="h-full rounded-full bg-indigo-500"
                      style={{ width: `${Math.round(src.relevance * 100)}%` }}
                    />
                  </div>
                  <span className="text-gray-500">{Math.round(src.relevance * 100)}%</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-3 text-sm text-white">
          {message.content}
        </div>
      </div>
    )
  }

  // Cortex response
  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl rounded-bl-md bg-white px-4 py-3 text-sm text-gray-800 ring-1 ring-gray-200 shadow-sm">
        {message.error ? (
          <p className="text-red-600">{message.content}</p>
        ) : (
          <>
            {message.skill && (
              <Link
                to={`/skills/${message.skill}`}
                className="inline-block mb-2 text-xs font-semibold text-indigo-600 hover:text-indigo-800 underline underline-offset-2"
              >
                Skill: {message.skill}
              </Link>
            )}

            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

            {message.confidence != null && (
              <div className="mt-2">
                <ConfidenceBadge score={message.confidence} />
              </div>
            )}

            <SourceCitations sources={message.sources} />
          </>
        )}
      </div>
    </div>
  )
}

export default function QueryPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)

  // Auto-scroll to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSubmit(question) {
    const q = (question ?? input).trim()
    if (!q || loading) return

    setInput('')

    // Add user message
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)

    try {
      const res = await queryKnowledge(q)
      const data = res.data

      setMessages((prev) => [
        ...prev,
        {
          role: 'cortex',
          content: data.readable_answer || 'No answer found.',
          skill: data.skill || null,
          sources: data.source_hits || [],
          confidence: data.confidence ?? null,
        },
      ])
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail || err.message || 'Something went wrong. Please try again.'
      setMessages((prev) => [
        ...prev,
        {
          role: 'cortex',
          content: errorMsg,
          error: true,
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  function handleChipClick(question) {
    handleSubmit(question)
  }

  const isEmpty = messages.length === 0

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Ask Cortex</h1>
        <p className="mt-1 text-sm text-gray-500">
          Ask questions about company processes
        </p>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto rounded-2xl bg-gray-50 ring-1 ring-gray-200 p-6 h-[calc(100vh-16rem)]">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-5xl mb-4 text-gray-300">?</div>
            <p className="text-gray-500 mb-6">
              Ask me anything about your company's processes
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => handleChipClick(q)}
                  className="rounded-full border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:border-indigo-400 hover:text-indigo-600 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md bg-white px-2 py-1 ring-1 ring-gray-200 shadow-sm">
                  <TypingIndicator />
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="mt-4 flex items-center gap-3">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your question..."
          disabled={loading}
          className="flex-1 rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          onClick={() => handleSubmit()}
          disabled={loading || !input.trim()}
          className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
            <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95l14.095-5.638a.75.75 0 0 0 0-1.392L3.105 2.289Z" />
          </svg>
          Send
        </button>
      </div>
    </div>
  )
}
