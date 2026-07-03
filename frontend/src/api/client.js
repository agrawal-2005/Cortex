import axios from 'axios'

// v2 API client (new /api/ routes)
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Legacy v1 client (for document listing)
const v1 = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

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

export function getIngestStatus(taskId) {
  return api.get('/ingest/status', { params: { task_id: taskId } })
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
