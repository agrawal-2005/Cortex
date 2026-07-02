import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getSkill, getFeedbackHistory, submitFeedback, deleteSkill } from '../api/client';
import ConfidenceBadge from '../components/ConfidenceBadge';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

const SOURCE_TYPE_ICONS = {
  slack: '\u{1F4AC}',
  jira: '\u{1F3AB}',
  notion: '\u{1F4DD}',
  upload: '\u{1F4C1}',
};

function getSourceIcon(documentId) {
  if (!documentId) return '\u{1F4C4}';
  const lower = documentId.toLowerCase();
  if (lower.includes('slack')) return SOURCE_TYPE_ICONS.slack;
  if (lower.includes('jira')) return SOURCE_TYPE_ICONS.jira;
  if (lower.includes('notion')) return SOURCE_TYPE_ICONS.notion;
  if (lower.includes('upload') || lower.includes('file')) return SOURCE_TYPE_ICONS.upload;
  return '\u{1F4C4}';
}

function truncateId(id, len = 16) {
  if (!id) return '';
  return id.length > len ? id.slice(0, len) + '\u2026' : id;
}

const feedbackBadgeColors = {
  approve: 'bg-green-100 text-green-800',
  edit: 'bg-yellow-100 text-yellow-800',
  reject: 'bg-red-100 text-red-800',
};

export default function SkillDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [skill, setSkill] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // View toggle
  const [viewMode, setViewMode] = useState('structured'); // 'structured' | 'plain'

  // Step expansion
  const [expandedSteps, setExpandedSteps] = useState({});

  // Feedback UI state
  const [feedbackMode, setFeedbackMode] = useState(null); // null | 'approve' | 'edit' | 'reject'
  const [editOriginal, setEditOriginal] = useState('');
  const [editCorrected, setEditCorrected] = useState('');
  const [feedbackReason, setFeedbackReason] = useState('');
  const [submittedBy, setSubmittedBy] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Delete
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [skillRes, feedbackRes] = await Promise.allSettled([
          getSkill(id),
          getFeedbackHistory(id),
        ]);

        if (skillRes.status === 'fulfilled') {
          setSkill(skillRes.value.data);
        } else {
          setError('Failed to load skill.');
          setLoading(false);
          return;
        }

        if (feedbackRes.status === 'fulfilled') {
          const fData = feedbackRes.value.data;
          if (Array.isArray(fData)) {
            setFeedback(fData);
          } else if (fData && Array.isArray(fData.items)) {
            setFeedback(fData.items);
          } else if (fData && Array.isArray(fData.feedback)) {
            setFeedback(fData.feedback);
          } else {
            setFeedback([]);
          }
        }
      } catch {
        setError('Failed to load skill details.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [id]);

  const toggleStep = (stepOrder) => {
    setExpandedSteps((prev) => ({ ...prev, [stepOrder]: !prev[stepOrder] }));
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this skill? This action cannot be undone.')) {
      return;
    }
    setDeleting(true);
    try {
      await deleteSkill(id);
      navigate('/');
    } catch {
      setError('Failed to delete skill.');
      setDeleting(false);
    }
  };

  const handleFeedbackAction = (action) => {
    if (action === 'approve') {
      handleSubmitFeedback('approve');
    } else {
      setFeedbackMode(action);
      setSubmitError(null);
      setSubmitSuccess(false);
    }
  };

  const handleSubmitFeedback = async (action) => {
    setSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);
    try {
      await submitFeedback({
        skill_id: id,
        action: action || feedbackMode,
        original_content: editOriginal.trim() || undefined,
        corrected_content: editCorrected.trim() || undefined,
        reason: feedbackReason.trim() || undefined,
        submitted_by: submittedBy.trim() || undefined,
      });

      // Refresh feedback list
      try {
        const res = await getFeedbackHistory(id);
        const fData = res.data;
        if (Array.isArray(fData)) {
          setFeedback(fData);
        } else if (fData && Array.isArray(fData.items)) {
          setFeedback(fData.items);
        } else if (fData && Array.isArray(fData.feedback)) {
          setFeedback(fData.feedback);
        }
      } catch {
        // silently fail on refresh
      }

      setEditOriginal('');
      setEditCorrected('');
      setFeedbackReason('');
      setSubmittedBy('');
      setFeedbackMode(null);
      setSubmitSuccess(true);
      setTimeout(() => setSubmitSuccess(false), 3000);
    } catch {
      setSubmitError('Failed to submit feedback.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner />
      </div>
    );
  }

  if (error && !skill) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="rounded-lg bg-red-50 p-6 text-red-700">{error}</div>
        <Link
          to="/"
          className="mt-4 inline-block text-sm text-indigo-600 hover:text-indigo-500"
        >
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  const lowConfidenceStepOrders = new Set(
    (skill.low_confidence_steps || []).map((s) => (typeof s === 'number' ? s : s?.step_order))
  );

  const sortedSteps = skill.steps
    ? [...skill.steps].sort((a, b) => (a.step_order ?? 0) - (b.step_order ?? 0))
    : [];

  const prerequisites = skill.skill_data?.prerequisites || skill.prerequisites || [];
  const edgeCases = skill.skill_data?.edge_cases || skill.edge_cases || [];
  const conditions = skill.skill_data?.conditions || skill.conditions || [];
  const rolesInvolved = skill.skill_data?.roles_involved || skill.roles_involved || [];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Back link */}
      <Link
        to="/"
        className="text-sm text-indigo-600 hover:text-indigo-500 mb-4 inline-block"
      >
        &larr; Back to Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">{skill.name}</h1>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status={skill.status} />
            <ConfidenceBadge score={skill.confidence} />
            {skill.department && (
              <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
                {skill.department}
              </span>
            )}
            {skill.version && (
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/20">
                v{skill.version}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-gray-500">
            {skill.extracted_at && (
              <span>Extracted: {formatDate(skill.extracted_at)}</span>
            )}
            {skill.verified_at && (
              <span>
                Verified: {formatDate(skill.verified_at)}
                {skill.verified_by ? ` by ${skill.verified_by}` : ''}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="flex-shrink-0 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          {deleting ? 'Deleting...' : 'Delete Skill'}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-700 text-sm">{error}</div>
      )}

      {/* Description */}
      {skill.description && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-5">
          <p className="text-gray-700 leading-relaxed">{skill.description}</p>
        </div>
      )}

      {/* View Toggle */}
      <div className="mb-6 flex items-center gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        <button
          onClick={() => setViewMode('structured')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            viewMode === 'structured'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Structured View
        </button>
        <button
          onClick={() => setViewMode('plain')}
          className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            viewMode === 'plain'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Plain English
        </button>
      </div>

      {viewMode === 'plain' ? (
        /* Plain English View */
        <section className="mb-8">
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <pre className="whitespace-pre-wrap text-sm text-gray-700 font-sans leading-relaxed">
              {skill.readable_text || 'No plain text version available.'}
            </pre>
          </div>
        </section>
      ) : (
        /* Structured View */
        <>
          {/* Steps Section */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Steps</h2>
            {sortedSteps.length > 0 ? (
              <div className="relative">
                {/* Vertical timeline line */}
                <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

                <div className="space-y-4">
                  {sortedSteps.map((step) => {
                    const isLowConfidence =
                      lowConfidenceStepOrders.has(step.step_order) ||
                      (step.confidence != null && step.confidence < 0.4);
                    const isExpanded = expandedSteps[step.step_order];
                    const details =
                      step.details && typeof step.details === 'object'
                        ? step.details
                        : null;
                    const detailsStr =
                      step.details && typeof step.details === 'string'
                        ? step.details
                        : null;

                    return (
                      <div
                        key={step.step_order}
                        className={`relative rounded-lg border bg-white p-4 ml-10 transition-colors ${
                          isLowConfidence
                            ? 'border-amber-300 bg-amber-50 border-l-4 border-l-amber-400'
                            : 'border-gray-200 border-l-4 border-l-indigo-300'
                        }`}
                      >
                        {/* Step number circle */}
                        <div
                          className={`absolute -left-14 top-4 flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold z-10 ${
                            isLowConfidence
                              ? 'bg-amber-100 text-amber-700 ring-2 ring-amber-300'
                              : 'bg-indigo-100 text-indigo-700 ring-2 ring-indigo-300'
                          }`}
                        >
                          {step.step_order}
                        </div>

                        {/* Step header */}
                        <button
                          onClick={() => toggleStep(step.step_order)}
                          className="w-full text-left"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-gray-900">{step.action}</p>
                              {step.confidence_label && (
                                <span className="text-xs text-gray-500">
                                  ({step.confidence_label})
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              {step.confidence != null && (
                                <ConfidenceBadge score={step.confidence} />
                              )}
                              <svg
                                className={`w-5 h-5 text-gray-400 transition-transform ${
                                  isExpanded ? 'rotate-180' : ''
                                }`}
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M19 9l-7 7-7-7"
                                />
                              </svg>
                            </div>
                          </div>
                        </button>

                        {/* Expanded details */}
                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                            {/* Explanation / details */}
                            {detailsStr && (
                              <div>
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                  Details
                                </h4>
                                <p className="text-sm text-gray-700">{detailsStr}</p>
                              </div>
                            )}
                            {details && (
                              <div className="space-y-2">
                                {details.explanation && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                      Explanation
                                    </h4>
                                    <p className="text-sm text-gray-700">{details.explanation}</p>
                                  </div>
                                )}
                                {details.tools && details.tools.length > 0 && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                      Tools
                                    </h4>
                                    <div className="flex flex-wrap gap-1.5">
                                      {details.tools.map((tool, i) => (
                                        <span
                                          key={i}
                                          className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20"
                                        >
                                          {tool}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {details.conditions && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                      Conditions
                                    </h4>
                                    <p className="text-sm text-gray-700">
                                      {typeof details.conditions === 'string'
                                        ? details.conditions
                                        : JSON.stringify(details.conditions)}
                                    </p>
                                  </div>
                                )}
                                {details.expected_output && (
                                  <div>
                                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                      Expected Output
                                    </h4>
                                    <p className="text-sm text-gray-700">{details.expected_output}</p>
                                  </div>
                                )}
                                {/* Render any remaining detail keys */}
                                {Object.entries(details)
                                  .filter(
                                    ([key]) =>
                                      !['explanation', 'tools', 'conditions', 'expected_output'].includes(key)
                                  )
                                  .map(([key, value]) => (
                                    <div key={key}>
                                      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                                        {key.replace(/_/g, ' ')}
                                      </h4>
                                      <p className="text-sm text-gray-700">
                                        {typeof value === 'string' ? value : JSON.stringify(value)}
                                      </p>
                                    </div>
                                  ))}
                              </div>
                            )}

                            {/* Sources */}
                            {step.sources && step.sources.length > 0 && (
                              <div>
                                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                                  Sources
                                </h4>
                                <div className="space-y-2">
                                  {step.sources.map((source, i) => (
                                    <div
                                      key={i}
                                      className="rounded-md bg-gray-50 p-3 text-sm border border-gray-100"
                                    >
                                      <div className="flex items-center justify-between mb-1">
                                        <span className="font-medium text-gray-700">
                                          {getSourceIcon(source.document_id)}{' '}
                                          {truncateId(source.document_id)}
                                        </span>
                                        {source.relevance_score != null && (
                                          <span className="text-xs text-gray-500">
                                            Relevance: {Math.round(source.relevance_score * 100)}%
                                          </span>
                                        )}
                                      </div>
                                      {source.snippet && (
                                        <p className="text-gray-600 italic text-xs mt-1">
                                          &ldquo;{source.snippet}&rdquo;
                                        </p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No steps defined.</p>
            )}
          </section>

          {/* Prerequisites */}
          {prerequisites.length > 0 && (
            <section className="mb-8">
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Prerequisites</h2>
                <ul className="list-disc list-inside space-y-1">
                  {prerequisites.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700">
                      {typeof item === 'string' ? item : JSON.stringify(item)}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          {/* Edge Cases */}
          {edgeCases.length > 0 && (
            <section className="mb-8">
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Edge Cases</h2>
                <ul className="list-disc list-inside space-y-1">
                  {edgeCases.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700">
                      {typeof item === 'string' ? item : JSON.stringify(item)}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          {/* Conditions */}
          {conditions.length > 0 && (
            <section className="mb-8">
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Conditions</h2>
                <ul className="list-disc list-inside space-y-1">
                  {conditions.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700">
                      {typeof item === 'string' ? item : JSON.stringify(item)}
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}

          {/* Roles */}
          {rolesInvolved.length > 0 && (
            <section className="mb-8">
              <div className="rounded-lg border border-gray-200 bg-white p-5">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">Roles Involved</h2>
                <div className="flex flex-wrap gap-2">
                  {rolesInvolved.map((role, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center rounded-full bg-purple-50 px-3 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-600/20"
                    >
                      {typeof role === 'string' ? role : JSON.stringify(role)}
                    </span>
                  ))}
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {/* Feedback Section */}
      <section className="mb-8">
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Feedback</h2>

          {/* Quick action buttons */}
          <div className="flex flex-wrap gap-3 mb-4">
            <button
              onClick={() => handleFeedbackAction('approve')}
              disabled={submitting}
              className="rounded-lg bg-green-600 px-5 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {submitting && feedbackMode === null ? 'Approving...' : 'Approve'}
            </button>
            <button
              onClick={() => handleFeedbackAction('edit')}
              disabled={submitting}
              className="rounded-lg bg-yellow-500 px-5 py-2 text-sm font-medium text-white hover:bg-yellow-600 disabled:opacity-50 transition-colors"
            >
              Edit
            </button>
            <button
              onClick={() => handleFeedbackAction('reject')}
              disabled={submitting}
              className="rounded-lg bg-red-600 px-5 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              Reject
            </button>
          </div>

          {submitSuccess && (
            <div className="mb-4 rounded-lg bg-green-50 p-3 text-green-700 text-sm">
              Feedback submitted successfully.
            </div>
          )}

          {/* Edit form */}
          {feedbackMode === 'edit' && (
            <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-yellow-800">Submit Edit Suggestion</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Original Content
                </label>
                <textarea
                  value={editOriginal}
                  onChange={(e) => setEditOriginal(e.target.value)}
                  placeholder="Paste the original content you want to change..."
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Corrected Content
                </label>
                <textarea
                  value={editCorrected}
                  onChange={(e) => setEditCorrected(e.target.value)}
                  placeholder="Provide the corrected version..."
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason
                </label>
                <textarea
                  value={feedbackReason}
                  onChange={(e) => setFeedbackReason(e.target.value)}
                  placeholder="Why is this change needed?"
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Name (optional)
                </label>
                <input
                  type="text"
                  value={submittedBy}
                  onChange={(e) => setSubmittedBy(e.target.value)}
                  placeholder="Your name"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              {submitError && (
                <p className="text-red-600 text-sm">{submitError}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => handleSubmitFeedback('edit')}
                  disabled={submitting}
                  className="rounded-lg bg-yellow-500 px-4 py-2 text-sm font-medium text-white hover:bg-yellow-600 disabled:opacity-50 transition-colors"
                >
                  {submitting ? 'Submitting...' : 'Submit Edit'}
                </button>
                <button
                  onClick={() => setFeedbackMode(null)}
                  className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Reject form */}
          {feedbackMode === 'reject' && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 space-y-3">
              <h3 className="text-sm font-semibold text-red-800">Reject Skill</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason for Rejection
                </label>
                <textarea
                  value={feedbackReason}
                  onChange={(e) => setFeedbackReason(e.target.value)}
                  placeholder="Why should this skill be rejected?"
                  rows={3}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Your Name (optional)
                </label>
                <input
                  type="text"
                  value={submittedBy}
                  onChange={(e) => setSubmittedBy(e.target.value)}
                  placeholder="Your name"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              {submitError && (
                <p className="text-red-600 text-sm">{submitError}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => handleSubmitFeedback('reject')}
                  disabled={submitting}
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {submitting ? 'Submitting...' : 'Submit Rejection'}
                </button>
                <button
                  onClick={() => setFeedbackMode(null)}
                  className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Feedback History */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Feedback History</h3>
            {feedback.length === 0 ? (
              <p className="text-gray-500 text-sm">No feedback yet.</p>
            ) : (
              <div className="space-y-3">
                {feedback.map((fb, idx) => (
                  <div
                    key={fb.id || idx}
                    className="rounded-lg border border-gray-200 bg-gray-50 p-4"
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          feedbackBadgeColors[fb.action] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {fb.action}
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatDate(fb.created_at)}
                      </span>
                      {fb.submitted_by && (
                        <span className="text-xs text-gray-500">by {fb.submitted_by}</span>
                      )}
                    </div>
                    {fb.reason && (
                      <p className="text-sm text-gray-700 mb-1">
                        <span className="font-medium">Reason:</span> {fb.reason}
                      </p>
                    )}
                    {fb.original_content && (
                      <p className="text-sm text-gray-500 mb-1">
                        <span className="font-medium">Original:</span> {fb.original_content}
                      </p>
                    )}
                    {fb.corrected_content && (
                      <p className="text-sm text-gray-700">
                        <span className="font-medium">Corrected:</span> {fb.corrected_content}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
