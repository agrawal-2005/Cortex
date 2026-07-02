"""Human-readable renderer for extracted skills.

Converts a structured Skill (with SkillSteps and StepSources) into
plain-English markdown suitable for the dashboard or API consumers.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.knowledge.models import Skill, SkillStep

# Confidence thresholds for display
_HIGH = 0.80
_MEDIUM = 0.50

_REVIEW_THRESHOLD = 0.80


def _confidence_indicator(score: float) -> str:
    """Return an ascii indicator for a confidence score."""
    pct = f"{score * 100:.0f}%"
    if score >= _HIGH:
        return f"[HIGH {pct}]"
    elif score >= _MEDIUM:
        return f"[MEDIUM {pct}]"
    return f"[LOW {pct}]"


def _format_date(dt: datetime | None) -> str:
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def render_skill_markdown(skill: Skill) -> str:
    """Render a Skill ORM object into readable Markdown.

    The skill should have its ``steps`` relationship loaded (e.g. via
    ``selectinload``).  Each step may have a ``sources`` relationship
    loaded for source-citation rendering.
    """
    lines: list[str] = []

    # ── Header ────────────────────────────────────────────────────────
    lines.append(f"# {skill.name}")
    lines.append("")

    meta_parts: list[str] = []
    if skill.department:
        meta_parts.append(f"**Department:** {skill.department}")
    meta_parts.append(f"**Status:** {skill.status.title()}")
    meta_parts.append(f"**Confidence:** {skill.confidence * 100:.0f}%")
    meta_parts.append(f"**Version:** {skill.version}")
    lines.append(" | ".join(meta_parts))
    lines.append("")

    # ── Description ───────────────────────────────────────────────────
    lines.append("## Description")
    lines.append(skill.description)
    lines.append("")

    # ── Prerequisites / Conditions ────────────────────────────────────
    skill_data: dict[str, Any] = skill.skill_data or {}

    prerequisites = skill_data.get("prerequisites", [])
    if prerequisites:
        lines.append("## Prerequisites")
        for p in prerequisites:
            lines.append(f"- {p}")
        lines.append("")

    conditions = skill_data.get("conditions", [])
    if conditions:
        lines.append("## Conditions")
        for c in conditions:
            lines.append(f"- {c}")
        lines.append("")

    # ── Steps ─────────────────────────────────────────────────────────
    steps: list[SkillStep] = sorted(skill.steps, key=lambda s: s.step_order)
    if steps:
        lines.append("## Steps")
        lines.append("")

        for step in steps:
            conf = _confidence_indicator(step.confidence)
            lines.append(f"### Step {step.step_order}: {step.action}  {conf}")

            details: dict[str, Any] = step.details or {}

            explanation = details.get("explanation", "")
            if explanation:
                lines.append(explanation)

            tools = details.get("tools", [])
            if tools:
                lines.append(f"- **Tools:** {', '.join(tools)}")

            step_condition = details.get("conditions") or details.get("condition")
            if step_condition:
                lines.append(f"- **When:** {step_condition}")

            expected = details.get("expected_output")
            if expected:
                lines.append(f"- **Expected output:** {expected}")

            # Source citations
            if hasattr(step, "sources") and step.sources:
                source_refs: list[str] = []
                for src in step.sources:
                    ref = f"doc:{src.document_id[:8]}"
                    if src.snippet:
                        ref += f' — "{src.snippet[:80]}"'
                    source_refs.append(ref)
                lines.append(f"- **Sources:** {'; '.join(source_refs)}")

            if step.depends_on:
                dep_labels = [f"Step {d}" for d in step.depends_on]
                lines.append(f"- **Depends on:** {', '.join(dep_labels)}")

            lines.append("")

    # ── Edge Cases ────────────────────────────────────────────────────
    edge_cases = skill_data.get("edge_cases", [])
    if edge_cases:
        lines.append("## Edge Cases")
        for ec in edge_cases:
            lines.append(f"- {ec}")
        lines.append("")

    # ── Roles ─────────────────────────────────────────────────────────
    roles = skill_data.get("roles_involved", [])
    if roles:
        lines.append("## Roles Involved")
        for r in roles:
            lines.append(f"- {r}")
        lines.append("")

    # ── Footer ────────────────────────────────────────────────────────
    lines.append("---")
    lines.append(
        f"*Extracted: {_format_date(skill.extracted_at)} | "
        f"Version {skill.version}*"
    )

    if skill.verified_by:
        lines.append(
            f"*Verified by {skill.verified_by} on "
            f"{_format_date(skill.verified_at)}*"
        )

    # Review warnings
    low_steps = [
        s for s in steps if s.confidence < _REVIEW_THRESHOLD
    ]
    if low_steps:
        labels = [
            f"Step {s.step_order} ({s.confidence * 100:.0f}%)"
            for s in low_steps
        ]
        lines.append(
            f"*>> FLAGGED FOR REVIEW: {', '.join(labels)} "
            f"below {_REVIEW_THRESHOLD * 100:.0f}% threshold*"
        )

    return "\n".join(lines)


def render_skill_plain(skill: Skill) -> str:
    """Render a Skill into a compact plain-text summary (no markdown).

    Useful for API responses or embedding context.
    """
    skill_data: dict[str, Any] = skill.skill_data or {}
    steps: list[SkillStep] = sorted(skill.steps, key=lambda s: s.step_order)

    parts: list[str] = [
        f"SKILL: {skill.name}",
        f"Status: {skill.status} | Confidence: {skill.confidence * 100:.0f}%",
        f"Department: {skill.department or 'General'}",
        "",
        skill.description,
        "",
    ]

    prerequisites = skill_data.get("prerequisites", [])
    if prerequisites:
        parts.append("Prerequisites: " + "; ".join(prerequisites))
        parts.append("")

    if steps:
        parts.append("STEPS:")
        for step in steps:
            details = step.details or {}
            explanation = details.get("explanation", "")
            line = f"  {step.step_order}. {step.action}"
            if explanation:
                line += f" — {explanation}"
            parts.append(line)
        parts.append("")

    edge_cases = skill_data.get("edge_cases", [])
    if edge_cases:
        parts.append("EDGE CASES:")
        for ec in edge_cases:
            parts.append(f"  - {ec}")

    return "\n".join(parts)


def render_skill_dict(skill: Skill) -> dict[str, Any]:
    """Render a Skill into a flat dictionary for JSON API responses.

    Includes the human-readable text alongside the structured data.
    """
    skill_data: dict[str, Any] = skill.skill_data or {}
    steps = sorted(skill.steps, key=lambda s: s.step_order)

    low_confidence_steps = [
        {
            "step_order": s.step_order,
            "action": s.action,
            "confidence": s.confidence,
        }
        for s in steps
        if s.confidence < _REVIEW_THRESHOLD
    ]

    return {
        "id": skill.id,
        "name": skill.name,
        "description": skill.description,
        "department": skill.department,
        "status": skill.status,
        "confidence": skill.confidence,
        "version": skill.version,
        "needs_review": bool(low_confidence_steps),
        "low_confidence_steps": low_confidence_steps,
        "steps": [
            {
                "step_order": s.step_order,
                "action": s.action,
                "details": s.details,
                "confidence": s.confidence,
                "confidence_label": _confidence_indicator(s.confidence),
                "sources": [
                    {
                        "document_id": src.document_id,
                        "snippet": src.snippet,
                        "relevance_score": src.relevance_score,
                    }
                    for src in (s.sources if hasattr(s, "sources") else [])
                ],
            }
            for s in steps
        ],
        "edge_cases": skill_data.get("edge_cases", []),
        "conditions": skill_data.get("conditions", []),
        "prerequisites": skill_data.get("prerequisites", []),
        "roles_involved": skill_data.get("roles_involved", []),
        "extracted_at": skill.extracted_at.isoformat() if skill.extracted_at else None,
        "verified_by": skill.verified_by,
        "verified_at": skill.verified_at.isoformat() if skill.verified_at else None,
        "readable_text": render_skill_plain(skill),
    }
