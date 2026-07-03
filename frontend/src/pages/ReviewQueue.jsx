import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronDown, ChevronRight, CheckCircle2, Pencil, XCircle,
  Inbox, ExternalLink,
} from 'lucide-react'
import { getSkills, getSkill, submitFeedback } from '../api/client'
import {
  StatusBadge, DeptBadge, ConfidenceBar, SkeletonCard, EmptyState, Button,
} from '../components/Primitives'
import Modal from '../components/Modal'
import { useToast } from '../components/Toast'

function StepPreview({ step }) {
  return (
    <div className="flex gap-3 py-2">
      <span className="w-6 h-6 rounded-full bg-primary/15 text-primary text-[11px] font-bold flex items-center justify-center shrink-0">
        {step.step_order}
      </span>
      <div className="min-w-0">
        <p className="text-sm text-text">{step.action}</p>
        {step.details?.explanation && (
          <p className="text-xs text-text-dim mt-0.5 line-clamp-2">{step.details.explanation}</p>
        )}
      </div>
    </div>
  )
}

function QueueItem({ skill, onAction }) {
  const [expanded, setExpanded] = useState(false)
  const [detail, setDetail] = useState(null)

  const toggle = () => {
    setExpanded((v) => !v)
    if (!detail) {
      getSkill(skill.id).then((res) => setDetail(res.data)).catch(() => {})
    }
  }

  return (
    <div className="card overflow-hidden">
      <button
        onClick={toggle}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-surface-2/60 transition-colors"
      >
        {expanded
          ? <ChevronDown size={16} className="text-text-dim shrink-0" />
          : <ChevronRight size={16} className="text-text-dim shrink-0" />}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text truncate">{skill.name}</p>
          <p className="text-xs text-text-dim truncate mt-0.5">{skill.description}</p>
        </div>
        <DeptBadge department={skill.department} />
        <StatusBadge status={skill.status} />
        <div className="w-32 hidden sm:block shrink-0">
          <ConfidenceBar value={skill.confidence} />
        </div>
      </button>

      {expanded && (
        <div className="border-t border-border px-5 py-4 space-y-4">
          {detail ? (
            <div className="divide-y divide-border/60">
              {[...(detail.steps || [])]
                .sort((a, b) => a.step_order - b.step_order)
                .map((s) => <StepPreview key={s.step_order} step={s} />)}
            </div>
          ) : (
            <p className="text-xs text-text-dim">Loading steps…</p>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="success" onClick={() => onAction(skill, 'approve')}>
              <CheckCircle2 size={14} /> Approve
            </Button>
            <Button variant="warning" onClick={() => onAction(skill, 'edit', detail)}>
              <Pencil size={14} /> Edit
            </Button>
            <Button variant="danger" onClick={() => onAction(skill, 'reject')}>
              <XCircle size={14} /> Reject
            </Button>
            <Link
              to={`/skills/${skill.id}`}
              className="ml-auto text-xs text-primary hover:underline flex items-center gap-1"
            >
              Full detail <ExternalLink size={11} />
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

export default function ReviewQueue() {
  const [skills, setSkills] = useState(null)
  const [modal, setModal] = useState(null) // {type: 'edit'|'reject', skill, detail?}
  const [reason, setReason] = useState('')
  const [corrected, setCorrected] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const toast = useToast()

  const load = useCallback(async () => {
    try {
      const [draft, review] = await Promise.all([
        getSkills({ status: 'draft', limit: 100 }),
        getSkills({ status: 'review', limit: 100 }),
      ])
      const merged = [...(draft.data.items || []), ...(review.data.items || [])]
      merged.sort((a, b) => (a.confidence || 0) - (b.confidence || 0))
      setSkills(merged)
    } catch {
      setSkills([])
    }
  }, [])

  useEffect(() => { load() }, [load])

  const removeFromQueue = (skillId) =>
    setSkills((prev) => prev.filter((s) => s.id !== skillId))

  const handleAction = async (skill, action, detail) => {
    if (action === 'approve') {
      try {
        await submitFeedback({ skill_id: skill.id, action: 'approve', submitted_by: 'reviewer' })
        removeFromQueue(skill.id)
        toast(`"${skill.name}" approved and marked as verified.`)
      } catch (e) {
        toast(e.response?.data?.detail || 'Approve failed.', 'error')
      }
      return
    }
    if (action === 'edit') {
      setCorrected(detail?.description || skill.description || '')
      setReason('')
      setModal({ type: 'edit', skill })
      return
    }
    setReason('')
    setModal({ type: 'reject', skill })
  }

  const submitModal = async () => {
    const { type, skill } = modal
    setSubmitting(true)
    try {
      await submitFeedback({
        skill_id: skill.id,
        action: type,
        original_content: type === 'edit' ? skill.description : undefined,
        corrected_content: type === 'edit' ? corrected : undefined,
        reason: reason || undefined,
        submitted_by: 'reviewer',
      })
      removeFromQueue(skill.id)
      toast(
        type === 'edit'
          ? `Correction submitted for "${skill.name}".`
          : `"${skill.name}" rejected.`,
        type === 'edit' ? 'success' : 'warning',
      )
      setModal(null)
    } catch (e) {
      toast(e.response?.data?.detail || 'Feedback failed.', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-text">Review Queue</h1>
        <p className="text-sm text-text-dim mt-1">
          Lowest-confidence skills first — these need the most attention.
        </p>
      </header>

      {!skills ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} lines={1} />)}
        </div>
      ) : skills.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="Queue is clear"
          message="No skills waiting for review. New extractions will appear here."
        />
      ) : (
        <div className="space-y-3">
          {skills.map((s) => (
            <QueueItem key={s.id} skill={s} onAction={handleAction} />
          ))}
        </div>
      )}

      {/* Edit / Reject modal */}
      <Modal
        open={!!modal}
        onClose={() => setModal(null)}
        title={modal?.type === 'edit' ? 'Edit skill' : 'Reject skill'}
        subtitle={modal?.skill?.name}
        wide={modal?.type === 'edit'}
      >
        <div className="space-y-4">
          {modal?.type === 'edit' && (
            <div>
              <label className="text-xs font-medium text-text-dim block mb-1.5">Corrected content</label>
              <textarea
                className="input-dark min-h-32 resize-y font-mono text-xs"
                value={corrected}
                onChange={(e) => setCorrected(e.target.value)}
              />
            </div>
          )}
          <div>
            <label className="text-xs font-medium text-text-dim block mb-1.5">
              Reason {modal?.type === 'edit' ? '(optional)' : ''}
            </label>
            <textarea
              className="input-dark min-h-20 resize-y"
              placeholder={
                modal?.type === 'edit'
                  ? 'What was wrong and why?'
                  : 'Why is this skill incorrect or outdated?'
              }
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button>
            <Button
              variant={modal?.type === 'edit' ? 'warning' : 'danger'}
              disabled={submitting || (modal?.type === 'reject' && !reason.trim())}
              onClick={submitModal}
            >
              {modal?.type === 'edit' ? 'Submit correction' : 'Reject skill'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
