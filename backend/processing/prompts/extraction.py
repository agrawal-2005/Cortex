"""Prompt templates for skill extraction.

These prompts instruct the LLM to extract a single structured, executable
skill from a cluster of related source documents.  Expert feedback from
previous review cycles is injected as hard context that overrides conflicting
source material.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# System-level instruction (persona + output schema)
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """\
You are Cortex, a company knowledge-extraction system.  Your job is to
analyze source documents gathered from company tools (Slack, Jira, Notion,
etc.) and synthesize them into a single structured, executable workflow
called a "skill".

Rules you MUST follow:
1. Every step MUST cite at least one source document by its ID.
2. Include a short verbatim quote ("snippet") from the cited document that
   supports the step.
3. If EXPERT CORRECTIONS are provided, they override any conflicting source
   material — treat them as ground truth.
4. Steps must be specific enough that someone unfamiliar with the process
   can execute them.
5. Identify edge cases that could cause the process to fail or branch.
6. Respond with ONLY the JSON object described below — no prose, no
   markdown fences, no commentary.

Output exactly ONE JSON object with this schema:

{
  "name": "<concise skill name>",
  "description": "<what this workflow does, when to use it, who runs it>",
  "department": "<engineering|support|operations|sales|hr|general>",
  "roles_involved": ["<role1>", "<role2>"],
  "steps": [
    {
      "step_order": 1,
      "action": "<short verb-phrase>",
      "details": {
        "explanation": "<how to do this step>",
        "tools": ["<tool1>"],
        "conditions": "<when this step applies — or null>",
        "expected_output": "<what should happen after this step>"
      },
      "source_document_ids": ["<doc-id>"],
      "source_snippets": ["<verbatim supporting quote>"]
    }
  ],
  "edge_cases": ["<edge-case description>"],
  "conditions": ["<prerequisite / pre-condition>"],
  "prerequisites": ["<what you need before starting>"]
}
"""


# ---------------------------------------------------------------------------
# Helpers to format documents and feedback for the prompt
# ---------------------------------------------------------------------------

def format_documents_for_prompt(documents: list[dict[str, Any]]) -> str:
    """Render a list of document dicts into the prompt section.

    Each document dict should contain at minimum ``id`` and ``content``.
    Optional keys: ``source_type``, ``channel_or_project``, ``author_name``,
    ``author_role``, ``created_at``, ``source_link``.
    """
    parts: list[str] = []
    for doc in documents:
        doc_id = doc.get("id", "unknown")
        source_type = doc.get("source_type", "unknown")
        channel = doc.get("channel_or_project", "")
        author = doc.get("author_name", "unknown")
        role = doc.get("author_role", "")
        created = doc.get("created_at")
        content = doc.get("content", "")

        # Format the date
        if isinstance(created, datetime):
            date_str = created.strftime("%Y-%m-%d")
        elif isinstance(created, str):
            date_str = created[:10]
        else:
            date_str = "unknown"

        # Build author line
        author_line = author
        if role:
            author_line = f"{author} ({role})"

        header_parts = [f"Source: {source_type}"]
        if channel:
            header_parts.append(f"Channel: #{channel}")
        header_parts.append(f"Author: {author_line}")
        header_parts.append(f"Date: {date_str}")
        header = " | ".join(header_parts)

        parts.append(
            f"=== DOCUMENT [{doc_id}] ===\n"
            f"{header}\n"
            f"---\n"
            f"{content}\n"
            f"=== END DOCUMENT ==="
        )

    return "\n\n".join(parts)


def format_feedback_for_prompt(feedback_items: list[dict[str, Any]]) -> str:
    """Render past expert feedback into the prompt section.

    Each feedback dict should contain ``action``, and optionally
    ``original_content``, ``corrected_content``, ``reason``,
    ``submitted_by``.
    """
    if not feedback_items:
        return "(No prior expert corrections for this topic.)"

    parts: list[str] = []
    for fb in feedback_items:
        action = fb.get("action", "edit")
        submitted_by = fb.get("submitted_by", "unknown")
        original = fb.get("original_content", "")
        corrected = fb.get("corrected_content", "")
        reason = fb.get("reason", "")

        lines = [
            f"=== EXPERT CORRECTION ({action.upper()}) ===",
            f"Submitted by: {submitted_by}",
        ]
        if original:
            lines.append(f'Original: "{original}"')
        if corrected:
            lines.append(f'Corrected: "{corrected}"')
        if reason:
            lines.append(f"Reason: {reason}")
        lines.append("=== END CORRECTION ===")

        parts.append("\n".join(lines))

    return "\n\n".join(parts)


def build_extraction_prompt(
    topic_label: str,
    documents: list[dict[str, Any]],
    feedback_items: list[dict[str, Any]],
) -> str:
    """Assemble the full user-turn prompt for skill extraction.

    Combines topic context, formatted documents, expert corrections,
    and the extraction instruction into a single string.
    """
    formatted_docs = format_documents_for_prompt(documents)
    formatted_feedback = format_feedback_for_prompt(feedback_items)

    return (
        f"## TOPIC CONTEXT\n"
        f"Topic: {topic_label}\n"
        f"Number of source documents: {len(documents)}\n\n"
        f"## SOURCE DOCUMENTS\n"
        f"{formatted_docs}\n\n"
        f"## EXPERT CORRECTIONS (from previous extraction reviews)\n"
        f"{formatted_feedback}\n\n"
        f"## TASK\n"
        f"Analyze ALL source documents above and extract exactly ONE "
        f"structured skill JSON object following the schema in your "
        f"instructions.  Every claim must cite its source document(s)."
    )
