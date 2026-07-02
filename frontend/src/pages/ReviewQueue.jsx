import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getSkills, submitFeedback } from '../api/client';
import ConfidenceBadge from '../components/ConfidenceBadge';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';

export default function ReviewQueue() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Track expanded cards
  const [expandedCards, setExpandedCards] = useState({});

  // Track reviewed items: { [skillId]: 'approved' | 'rejected' | 'editing' }
  const [reviewedItems, setReviewedItems] = useState({});

  // Per-step feedback state: { [skillId-stepOrder]: { mode, reason, original, corrected } }
  const [stepFeedback, setStepFeedback] = useState({});

  // Submission states
  const [submittingSkills, setSubmittingSkills] = useState({});
  const [submittingSteps, setSubmittingSteps] = useState({});

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const res = await getSkills({ status: 'review', limit: 100 });
        const data = res.data;
        let items = [];
        if (Array.isArray(data)) {
          items = data;
        } else if (data && Array.isArray(data.items)) {
          items = data.items;
        } else if (data && Array.isArray(data.skills)) {
          items = data.skills;
        }
        // Sort by confidence ascending (lowest first)
        items.sort((a, b) => (a.confidence ?? 0) - (b.confidence ?? 0));
        setSkills(items);
      } catch {
        setError('Failed to load review queue.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const toggleCard = (skillId) => {
    setExpandedCards((prev) => ({ ...prev, [skillId]: !prev[skillId] }));
  };

  const handleApproveAll = async (skill) => {
    setSubmittingSkills((prev) => ({ ...prev, [skill.id]: true }));
    try {
      await submitFeedback({
        skill_id: skill.id,
        action: 'approve',
      });
      setReviewedItems((prev) => ({ ...prev, [skill.id]: 'approved' }));
    } catch {
      setError(`Failed to approve "${skill.name}".`);
    } finally {
      setSubmittingSkills((prev) => ({ ...prev, [skill.id]: false }));
    }
  };

  const handleStepAction = async (skillId, step, action) => {
    const key = `${skillId}-${step.step_order}`;

    if (action === 'edit') {
      setStepFeedback((prev) => ({
        ...prev,
        [key]: { mode: 'edit', reason: '', original: step.action, corrected: '' },
      }));
      return;
    }

    if (action === 'reject') {
      setStepFeedback((prev) => ({
        ...prev,
        [key]: { mode: 'reject', reason: '' },
      }));
      return;
    }

    // Approve
    setSubmittingSteps((prev) => ({ ...prev, [key]: true }));
    try {
      await submitFeedback({
        skill_id: skillId,
        step_id: step.id || step.step_order,
        action,
      });
      setStepFeedback((prev) => ({
        ...prev,
        [key]: { mode: 'done', action },
      }));
    } catch {
      setError(`Failed to ${action} step ${step.step_order}.`);
    } finally {
      setSubmittingSteps((prev) => ({ ...prev, [key]: false }));
    }
  };

  const handleStepFeedbackSubmit = async (skillId, step) => {
    const key = `${skillId}-${step.step_order}`;
    const fb = stepFeedback[key];
    if (!fb) return;

    setSubmittingSteps((prev) => ({ ...prev, [key]: true }));
    try {
      await submitFeedback({
        skill_id: skillId,
        step_id: step.id || step.step_order,
        action: fb.mode,
        original_content: fb.original?.trim() || undefined,
        corrected_content: fb.corrected?.trim() || undefined,
        reason: fb.reason?.trim() || undefined,
      });
      setStepFeedback((prev) => ({
        ...prev,
        [key]: { mode: 'done', action: fb.mode },
      }));
    } catch {
      setError(`Failed to submit feedback for step ${step.step_order}.`);
    } finally {
      setSubmittingSteps((prev) => ({ ...prev, [key]: false }));
    }
  };

  const updateStepFeedback = (key, field, value) => {
    setStepFeedback((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  };

  const cancelStepFeedback = (key) => {
    setStepFeedback((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const unreviewedSkills = skills.filter((s) => !reviewedItems[s.id]);
  const approvedSkills = skills.filter((s) => reviewedItems[s.id] === 'approved');

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Review Queue</h1>
        <span className="inline-flex items-center rounded-full bg-yellow-100 px-3 py-1 text-sm font-semibold text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
          {unreviewedSkills.length}
        </span>
      </div>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 p-4 text-red-700 text-sm">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-3 text-red-500 hover:text-red-700 font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Empty state */}
      {unreviewedSkills.length === 0 && approvedSkills.length === 0 && (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">{'\u{1F389}'}</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No skills pending review</h2>
          <p className="text-gray-500 mb-6">All skills have been reviewed. Great work!</p>
          <Link
            to="/"
            className="inline-flex items-center rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            Back to Dashboard
          </Link>
        </div>
      )}

      {/* Unreviewed skills */}
      {unreviewedSkills.length > 0 && (
        <div className="space-y-4 mb-8">
          {unreviewedSkills.map((skill) => {
            const isExpanded = expandedCards[skill.id];
            const isSubmitting = submittingSkills[skill.id];
            const sortedSteps = skill.steps
              ? [...skill.steps].sort((a, b) => (a.step_order ?? 0) - (b.step_order ?? 0))
              : [];
            const lowConfSteps = skill.low_confidence_steps || [];
            const confidencePct = Math.round((skill.confidence ?? 0) * 100);

            return (
              <div
                key={skill.id}
                className="rounded-lg border border-amber-200 bg-amber-50 shadow-sm transition-all"
              >
                {/* Card header */}
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <button
                      onClick={() => toggleCard(skill.id)}
                      className="flex-1 text-left"
                    >
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{skill.name}</h3>
                        <StatusBadge status={skill.status} />
                      </div>
                      <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                        {skill.department && (
                          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                            {skill.department}
                          </span>
                        )}
                        <span>{sortedSteps.length} steps</span>
                        {lowConfSteps.length > 0 && (
                          <span className="text-amber-700 font-medium">
                            {lowConfSteps.length} low confidence step{lowConfSteps.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>

                      {/* Confidence bar */}
                      <div className="mt-3 flex items-center gap-3">
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${
                              confidencePct > 70
                                ? 'bg-green-500'
                                : confidencePct > 40
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                            }`}
                            style={{ width: `${confidencePct}%` }}
                          />
                        </div>
                        <ConfidenceBadge score={skill.confidence} />
                      </div>
                    </button>

                    {/* Expand chevron */}
                    <button
                      onClick={() => toggleCard(skill.id)}
                      className="ml-3 p-1 text-gray-400 hover:text-gray-600"
                    >
                      <svg
                        className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
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
                    </button>
                  </div>

                  {/* Quick actions */}
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => handleApproveAll(skill)}
                      disabled={isSubmitting}
                      className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                    >
                      {isSubmitting ? 'Approving...' : 'Approve All'}
                    </button>
                    <Link
                      to={`/skills/${skill.id}`}
                      className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
                    >
                      View Detail
                    </Link>
                  </div>
                </div>

                {/* Expanded inline review */}
                {isExpanded && (
                  <div className="border-t border-amber-200 bg-white rounded-b-lg p-5">
                    {sortedSteps.length === 0 ? (
                      <p className="text-gray-500 text-sm">No steps to review.</p>
                    ) : (
                      <div className="space-y-3">
                        {sortedSteps.map((step) => {
                          const key = `${skill.id}-${step.step_order}`;
                          const fb = stepFeedback[key];
                          const isStepSubmitting = submittingSteps[key];
                          const isLowConf =
                            (step.confidence != null && step.confidence < 0.4) ||
                            lowConfSteps.some(
                              (s) => (typeof s === 'number' ? s : s?.step_order) === step.step_order
                            );

                          return (
                            <div
                              key={step.step_order}
                              className={`rounded-lg border p-4 ${
                                fb?.mode === 'done'
                                  ? 'border-green-200 bg-green-50'
                                  : isLowConf
                                  ? 'border-amber-300 bg-amber-50'
                                  : 'border-gray-200 bg-white'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                  <span
                                    className={`flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold ${
                                      isLowConf
                                        ? 'bg-amber-100 text-amber-700'
                                        : 'bg-indigo-100 text-indigo-700'
                                    }`}
                                  >
                                    {step.step_order}
                                  </span>
                                  <p className="font-medium text-gray-900">{step.action}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                  {step.confidence != null && (
                                    <ConfidenceBadge score={step.confidence} />
                                  )}
                                  {fb?.mode === 'done' && (
                                    <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                                      {fb.action === 'approve'
                                        ? 'Approved'
                                        : fb.action === 'edit'
                                        ? 'Edited'
                                        : 'Rejected'}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Step action buttons */}
                              {(!fb || (fb.mode !== 'done' && fb.mode !== 'edit' && fb.mode !== 'reject')) && (
                                <div className="flex gap-2 mt-3">
                                  <button
                                    onClick={() => handleStepAction(skill.id, step, 'approve')}
                                    disabled={isStepSubmitting}
                                    className="rounded-md bg-green-100 px-3 py-1 text-xs font-medium text-green-700 hover:bg-green-200 disabled:opacity-50 transition-colors"
                                  >
                                    {isStepSubmitting ? '...' : 'Approve'}
                                  </button>
                                  <button
                                    onClick={() => handleStepAction(skill.id, step, 'edit')}
                                    disabled={isStepSubmitting}
                                    className="rounded-md bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-700 hover:bg-yellow-200 disabled:opacity-50 transition-colors"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    onClick={() => handleStepAction(skill.id, step, 'reject')}
                                    disabled={isStepSubmitting}
                                    className="rounded-md bg-red-100 px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-200 disabled:opacity-50 transition-colors"
                                  >
                                    Reject
                                  </button>
                                </div>
                              )}

                              {/* Inline edit form */}
                              {fb?.mode === 'edit' && (
                                <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
                                  <textarea
                                    value={fb.corrected || ''}
                                    onChange={(e) => updateStepFeedback(key, 'corrected', e.target.value)}
                                    placeholder="Enter corrected content..."
                                    rows={2}
                                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                  />
                                  <textarea
                                    value={fb.reason || ''}
                                    onChange={(e) => updateStepFeedback(key, 'reason', e.target.value)}
                                    placeholder="Reason for the edit (optional)..."
                                    rows={1}
                                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                  />
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => handleStepFeedbackSubmit(skill.id, step)}
                                      disabled={isStepSubmitting}
                                      className="rounded-md bg-yellow-500 px-3 py-1 text-xs font-medium text-white hover:bg-yellow-600 disabled:opacity-50 transition-colors"
                                    >
                                      {isStepSubmitting ? 'Submitting...' : 'Submit Edit'}
                                    </button>
                                    <button
                                      onClick={() => cancelStepFeedback(key)}
                                      className="rounded-md bg-gray-200 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300 transition-colors"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              )}

                              {/* Inline reject form */}
                              {fb?.mode === 'reject' && (
                                <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
                                  <textarea
                                    value={fb.reason || ''}
                                    onChange={(e) => updateStepFeedback(key, 'reason', e.target.value)}
                                    placeholder="Reason for rejection..."
                                    rows={2}
                                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                  />
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => handleStepFeedbackSubmit(skill.id, step)}
                                      disabled={isStepSubmitting}
                                      className="rounded-md bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                                    >
                                      {isStepSubmitting ? 'Submitting...' : 'Submit Rejection'}
                                    </button>
                                    <button
                                      onClick={() => cancelStepFeedback(key)}
                                      className="rounded-md bg-gray-200 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-300 transition-colors"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Approved / reviewed section */}
      {approvedSkills.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-700 mb-3">
            Recently Reviewed ({approvedSkills.length})
          </h2>
          <div className="space-y-3">
            {approvedSkills.map((skill) => (
              <div
                key={skill.id}
                className="rounded-lg border border-green-200 bg-green-50 p-4 flex items-center justify-between transition-all"
              >
                <div className="flex items-center gap-3">
                  <span className="text-green-600 font-medium">{'\u2713'}</span>
                  <div>
                    <h3 className="font-medium text-gray-900">{skill.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      {skill.department && (
                        <span className="text-xs text-gray-500">{skill.department}</span>
                      )}
                      <ConfidenceBadge score={skill.confidence} />
                    </div>
                  </div>
                </div>
                <Link
                  to={`/skills/${skill.id}`}
                  className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
                >
                  View Detail
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
