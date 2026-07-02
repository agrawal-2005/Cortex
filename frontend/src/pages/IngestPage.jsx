import { useState, useRef, useEffect, useCallback } from 'react'
import { uploadSlackExport, uploadFile, getIngestStatus, getDocuments } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge from '../components/StatusBadge'

const SOURCE_TYPES = [
  { value: 'jira', label: 'Jira' },
  { value: 'notion', label: 'Notion' },
  { value: 'confluence', label: 'Confluence' },
  { value: 'custom', label: 'Custom' },
]

const SLACK_STAGES = ['extracting', 'parsing', 'ingesting', 'embedding']

function DropZone({ label, icon, accept, hint, dragActive, onDragOver, onDragLeave, onDrop, onClick, uploading, children }) {
  let borderClasses = 'border-dashed border-2 border-gray-300 bg-gray-50'
  if (uploading) {
    borderClasses = 'border-solid border-2 border-blue-500 bg-blue-50'
  } else if (dragActive) {
    borderClasses = 'border-dashed border-2 border-indigo-500 bg-indigo-50'
  }

  return (
    <div
      className={`rounded-xl p-8 text-center cursor-pointer transition-colors ${borderClasses}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={onClick}
    >
      <div className="text-4xl mb-3 text-gray-400">{icon}</div>
      <p className="text-sm font-semibold text-gray-700 mb-1">{label}</p>
      <p className="text-xs text-gray-500">{hint}</p>
      {children}
    </div>
  )
}

function StageProgress({ currentStage }) {
  return (
    <div className="mt-4 space-y-1">
      {SLACK_STAGES.map((stage) => {
        const idx = SLACK_STAGES.indexOf(stage)
        const currentIdx = SLACK_STAGES.indexOf(currentStage)
        let color = 'text-gray-400'
        let marker = '○'
        if (idx < currentIdx) {
          color = 'text-green-600'
          marker = '✓'
        } else if (idx === currentIdx) {
          color = 'text-indigo-600 font-semibold'
          marker = '●'
        }
        return (
          <div key={stage} className={`flex items-center gap-2 text-sm ${color}`}>
            <span>{marker}</span>
            <span className="capitalize">{stage}</span>
          </div>
        )
      })}
    </div>
  )
}

export default function IngestPage() {
  // Slack upload state
  const [slackFile, setSlackFile] = useState(null)
  const [slackDragActive, setSlackDragActive] = useState(false)
  const [slackUploading, setSlackUploading] = useState(false)
  const [slackTaskId, setSlackTaskId] = useState(null)
  const [slackStatus, setSlackStatus] = useState(null)
  const [slackProgress, setSlackProgress] = useState(null)
  const [slackResult, setSlackResult] = useState(null)
  const [slackError, setSlackError] = useState(null)
  const slackInputRef = useRef(null)
  const pollRef = useRef(null)

  // File upload state
  const [fileData, setFileData] = useState(null)
  const [fileDragActive, setFileDragActive] = useState(false)
  const [fileUploading, setFileUploading] = useState(false)
  const [fileSourceType, setFileSourceType] = useState('jira')
  const [fileResult, setFileResult] = useState(null)
  const [fileError, setFileError] = useState(null)
  const fileInputRef = useRef(null)

  // Recent documents
  const [recentDocs, setRecentDocs] = useState([])
  const [docsLoading, setDocsLoading] = useState(true)

  // Fetch recent documents
  const fetchDocs = useCallback(async () => {
    try {
      setDocsLoading(true)
      const res = await getDocuments({ limit: 10 })
      setRecentDocs(res.data?.documents ?? res.data ?? [])
    } catch {
      // silently ignore
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocs()
  }, [fetchDocs])

  // Poll Slack ingest status
  useEffect(() => {
    if (!slackTaskId || slackStatus === 'completed' || slackStatus === 'failed') return

    pollRef.current = setInterval(async () => {
      try {
        const res = await getIngestStatus(slackTaskId)
        const data = res.data
        setSlackStatus(data.status)
        setSlackProgress(data.progress)

        if (data.status === 'completed') {
          setSlackResult(data.progress)
          setSlackUploading(false)
          clearInterval(pollRef.current)
          fetchDocs()
        } else if (data.status === 'failed') {
          setSlackError(data.error || 'Ingestion failed')
          setSlackUploading(false)
          clearInterval(pollRef.current)
        }
      } catch {
        setSlackError('Failed to check ingestion status')
        setSlackUploading(false)
        clearInterval(pollRef.current)
      }
    }, 2000)

    return () => clearInterval(pollRef.current)
  }, [slackTaskId, slackStatus, fetchDocs])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  // ── Slack handlers ──

  function handleSlackDragOver(e) {
    e.preventDefault()
    e.stopPropagation()
    setSlackDragActive(true)
  }

  function handleSlackDragLeave(e) {
    e.preventDefault()
    e.stopPropagation()
    setSlackDragActive(false)
  }

  function handleSlackDrop(e) {
    e.preventDefault()
    e.stopPropagation()
    setSlackDragActive(false)
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.endsWith('.zip')) {
      setSlackFile(file)
      setSlackError(null)
      setSlackResult(null)
      doSlackUpload(file)
    } else {
      setSlackError('Please drop a .zip file')
    }
  }

  function handleSlackFileSelect(e) {
    const file = e.target.files?.[0]
    if (file && file.name.endsWith('.zip')) {
      setSlackFile(file)
      setSlackError(null)
      setSlackResult(null)
      doSlackUpload(file)
    } else if (file) {
      setSlackError('Please select a .zip file')
    }
  }

  async function doSlackUpload(file) {
    setSlackUploading(true)
    setSlackStatus('running')
    setSlackProgress(null)
    setSlackError(null)
    setSlackResult(null)

    try {
      const res = await uploadSlackExport(file)
      const data = res.data
      if (data.task_id) {
        setSlackTaskId(data.task_id)
        setSlackStatus(data.status || 'running')
      } else {
        // Synchronous completion
        setSlackResult(data)
        setSlackStatus('completed')
        setSlackUploading(false)
        fetchDocs()
      }
    } catch (err) {
      setSlackError(err.response?.data?.detail || err.message || 'Upload failed')
      setSlackUploading(false)
      setSlackStatus(null)
    }
  }

  // ── File upload handlers ──

  function handleFileDragOver(e) {
    e.preventDefault()
    e.stopPropagation()
    setFileDragActive(true)
  }

  function handleFileDragLeave(e) {
    e.preventDefault()
    e.stopPropagation()
    setFileDragActive(false)
  }

  function handleFileDrop(e) {
    e.preventDefault()
    e.stopPropagation()
    setFileDragActive(false)
    const file = e.dataTransfer.files?.[0]
    if (file && (file.name.endsWith('.csv') || file.name.endsWith('.json'))) {
      setFileData(file)
      setFileError(null)
      setFileResult(null)
    } else {
      setFileError('Please drop a .csv or .json file')
    }
  }

  function handleFileSelect(e) {
    const file = e.target.files?.[0]
    if (file && (file.name.endsWith('.csv') || file.name.endsWith('.json'))) {
      setFileData(file)
      setFileError(null)
      setFileResult(null)
    } else if (file) {
      setFileError('Please select a .csv or .json file')
    }
  }

  async function doFileUpload() {
    if (!fileData) return
    setFileUploading(true)
    setFileError(null)
    setFileResult(null)

    try {
      const res = await uploadFile(fileData, fileSourceType)
      setFileResult(res.data)
      setFileData(null)
      fetchDocs()
    } catch (err) {
      setFileError(err.response?.data?.detail || err.message || 'Upload failed')
    } finally {
      setFileUploading(false)
    }
  }

  // ── Helpers ──

  function slackCurrentStage() {
    if (!slackProgress) return null
    if (typeof slackProgress === 'string') return slackProgress
    return slackProgress.stage || slackProgress.current_stage || null
  }

  function formatDate(dateStr) {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
  }

  function truncate(str, len = 80) {
    if (!str) return '-'
    return str.length > len ? str.slice(0, len) + '...' : str
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Ingest Data</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload Slack exports or structured files to build your knowledge base.
        </p>
      </div>

      {/* Upload zones — two columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left — Slack Export */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Slack Export</h2>

          <DropZone
            label="Drop Slack export here"
            icon="#"
            accept=".zip"
            hint="Accepts .zip files exported from Slack"
            dragActive={slackDragActive}
            uploading={slackUploading}
            onDragOver={handleSlackDragOver}
            onDragLeave={handleSlackDragLeave}
            onDrop={handleSlackDrop}
            onClick={() => slackInputRef.current?.click()}
          >
            <input
              ref={slackInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={handleSlackFileSelect}
            />

            {slackFile && (
              <p className="mt-3 text-sm font-medium text-indigo-700">
                {slackFile.name}
              </p>
            )}

            {slackUploading && (
              <div className="mt-4">
                <LoadingSpinner size="sm" />
                {slackCurrentStage() && (
                  <StageProgress currentStage={slackCurrentStage()} />
                )}
              </div>
            )}
          </DropZone>

          {slackError && (
            <p className="mt-3 text-sm text-red-600">{slackError}</p>
          )}

          {slackResult && (
            <div className="mt-4 rounded-lg bg-green-50 p-4 text-sm text-green-800 space-y-1">
              <p className="font-semibold">Ingestion complete</p>
              {slackResult.documents_ingested != null && (
                <p>Documents ingested: {slackResult.documents_ingested}</p>
              )}
              {slackResult.channels_processed != null && (
                <p>Channels processed: {slackResult.channels_processed}</p>
              )}
              {slackResult.messages_processed != null && (
                <p>Messages processed: {slackResult.messages_processed}</p>
              )}
            </div>
          )}
        </div>

        {/* Right — File Upload */}
        <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">File Upload</h2>

          <DropZone
            label="Drop CSV or JSON file here"
            icon="↑"
            accept=".csv,.json"
            hint="Accepts .csv and .json files"
            dragActive={fileDragActive}
            uploading={fileUploading}
            onDragOver={handleFileDragOver}
            onDragLeave={handleFileDragLeave}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.json"
              className="hidden"
              onChange={handleFileSelect}
            />

            {fileData && (
              <p className="mt-3 text-sm font-medium text-indigo-700">
                {fileData.name}
              </p>
            )}

            {fileUploading && (
              <div className="mt-4">
                <LoadingSpinner size="sm" />
              </div>
            )}
          </DropZone>

          {fileData && !fileUploading && (
            <div className="mt-4 flex items-end gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Source type
                </label>
                <select
                  value={fileSourceType}
                  onChange={(e) => setFileSourceType(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {SOURCE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={doFileUpload}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
              >
                Upload
              </button>
            </div>
          )}

          {fileError && (
            <p className="mt-3 text-sm text-red-600">{fileError}</p>
          )}

          {fileResult && (
            <div className="mt-4 rounded-lg bg-green-50 p-4 text-sm text-green-800 space-y-1">
              <p className="font-semibold">Upload complete</p>
              {fileResult.documents_created != null && (
                <p>Documents created: {fileResult.documents_created}</p>
              )}
              {fileResult.skipped != null && (
                <p>Skipped: {fileResult.skipped}</p>
              )}
              {fileResult.errors != null && (
                <p>Errors: {Array.isArray(fileResult.errors) ? fileResult.errors.length : fileResult.errors}</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent ingestion history */}
      <div className="bg-white rounded-2xl shadow-sm ring-1 ring-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-800">Recent Ingestions</h2>
        </div>

        {docsLoading ? (
          <LoadingSpinner className="py-12" />
        ) : recentDocs.length === 0 ? (
          <p className="px-6 py-12 text-center text-sm text-gray-400">
            No documents ingested yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3">Content</th>
                  <th className="px-6 py-3">Source Type</th>
                  <th className="px-6 py-3">Channel</th>
                  <th className="px-6 py-3">Author</th>
                  <th className="px-6 py-3">Ingested At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentDocs.map((doc, i) => (
                  <tr key={doc.id ?? doc.document_id ?? i} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-gray-700 max-w-xs truncate">
                      {truncate(doc.content_snippet || doc.content || doc.title)}
                    </td>
                    <td className="px-6 py-3">
                      <StatusBadge status={doc.source_type || 'unknown'} />
                    </td>
                    <td className="px-6 py-3 text-gray-600">
                      {doc.channel || doc.metadata?.channel || '-'}
                    </td>
                    <td className="px-6 py-3 text-gray-600">
                      {doc.author || doc.metadata?.author || '-'}
                    </td>
                    <td className="px-6 py-3 text-gray-500 whitespace-nowrap">
                      {formatDate(doc.ingested_at || doc.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
