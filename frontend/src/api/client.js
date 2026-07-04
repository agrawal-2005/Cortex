import axios from 'axios'

// API key: localStorage override (settable at runtime) > build-time env.
function apiKey() {
  return localStorage.getItem('cortex_api_key') || import.meta.env.VITE_API_KEY || ''
}

function withAuth(instance) {
  instance.interceptors.request.use((config) => {
    const key = apiKey()
    if (key) config.headers['X-API-Key'] = key
    return config
  })
  return instance
}

// v2 API client (new /api/ routes)
const api = withAuth(
  axios.create({
    baseURL: '/api',
    headers: { 'Content-Type': 'application/json' },
  })
)

// Legacy v1 client (for document listing)
const v1 = withAuth(
  axios.create({
    baseURL: '/api/v1',
    headers: { 'Content-Type': 'application/json' },
  })
)

// ── Skills ──────────────────────────────────────────────────────────────────

export function getSkills(params = {}) {
  return api.get('/skills/', { params })
}

export function getSkill(id) {
  return api.get(`/skills/${id}`)
}

export function getExecutableSkill(id) {
  return api.get(`/skills/${id}/executable`)
}

export function createSkill(data) {
  return v1.post('/skills/', data)
}

export function searchSkills(query) {
  return v1.get('/skills/search', { params: { query } })
}

export function deleteSkill(id) {
  return v1.delete(`/skills/${id}`)
}

// ── Documents ───────────────────────────────────────────────────────────────

export function getDocuments(params = {}) {
  return v1.get('/ingest/documents', { params })
}

export function getDocumentSourceTypes() {
  return v1.get('/ingest/documents/source-types')
}

// ── Ingestion ───────────────────────────────────────────────────────────────

export function uploadSlackExport(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/ingest/slack', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function uploadFile(file, sourceType) {
  const form = new FormData()
  form.append('file', file)
  form.append('source_type', sourceType)
  return api.post('/ingest/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function uploadJiraExport(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/ingest/jira', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function uploadConfluenceExport(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/ingest/confluence', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getIngestStatus(taskId) {
  return api.get('/ingest/status', { params: { task_id: taskId } })
}

export function ingestGitHub({ repo, token, months = 6, includeComments = true }) {
  return api.post('/ingest/github', {
    repo,
    token: token || null,
    months,
    include_comments: includeComments,
  })
}

export function uploadDiscordExport(file) {
  const form = new FormData()
  form.append('file', file)
  return api.post('/ingest/discord/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function ingestDiscordLive({ guildId, channelIds, botToken }) {
  return api.post('/ingest/discord/live', {
    guild_id: guildId,
    channel_ids: channelIds,
    bot_token: botToken || null,
  })
}

// ── Processing (skill extraction) ───────────────────────────────────────────

const v1Processing = withAuth(axios.create({ baseURL: '/api/v1/processing' }))

export function clusterDocuments(limit = 500) {
  return v1Processing.post('/cluster', null, { params: { limit } })
}

export function extractAllClusters(clusters) {
  return v1Processing.post('/extract-all', clusters)
}

// ── Query ───────────────────────────────────────────────────────────────────

export function queryKnowledge(question) {
  return api.post('/query/', { question })
}

// ── Feedback ────────────────────────────────────────────────────────────────

export function submitFeedback(data) {
  return api.post('/feedback/', data)
}

export function getFeedbackHistory(skillId, params = {}) {
  return api.get(`/feedback/history/${skillId}`, { params })
}

export default api
