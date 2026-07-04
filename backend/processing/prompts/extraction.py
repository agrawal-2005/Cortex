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
etc.) and synthesize them into a single structured, AUTOMATION-READY
workflow called a "skill" — a procedure precise enough that a software
agent could execute it, not just a summary a human could read.

## STEP 0 — REPEATABILITY CHECK (do this before anything else)

First determine if this cluster describes a REPEATABLE WORKFLOW (runs many
times, e.g. "handle a refund") or a ONE-TIME PROJECT (happened once, e.g.
"implement the identity system in Q1"). Only extract repeatable workflows
as skills. For one-time projects, return
{"is_skill": false, "reason": "one-time project, not a repeatable workflow"}
and nothing else.

A repeatable workflow operates on INPUTS that change between runs (a
different repo, a different PR number, a different customer). If you cannot
name the inputs the workflow operates on, it is probably not a real skill.

## RULES you MUST follow

1. QUOTE, don't summarize. If a source document contains a specific
   command, code snippet, API endpoint, config value, or exact string that
   a person would type or run, you MUST include it verbatim in the step.
   Never replace a concrete command with a description of the command.
   BAD:  "comment with the appropriate ignore command"
   GOOD: "comment: '@dependabot ignore this major version' (for major) or
          '@dependabot ignore this dependency' (to ignore entirely)"
2. Every skill MUST declare "inputs_schema": the parameters it operates on
   (e.g. for a Dependabot workflow: {"repo": "...", "pr_number": "..."}).
   Reference inputs inside steps as template values like {{input.repo}}.
3. Every step MUST cite at least one source document by its ID, with a
   short verbatim quote ("snippet") that supports the step.
4. If EXPERT CORRECTIONS are provided, they override any conflicting source
   material — treat them as ground truth.
5. Steps must be specific enough that someone (or something) unfamiliar
   with the process can execute them: concrete tool, concrete invocation,
   machine-checkable success criteria, and what to do on failure.
6. Identify edge cases that could cause the process to fail or branch.
7. Assess automation_readiness HONESTLY:
   - "executable" = has inputs, concrete commands, success criteria, and
     error handling for every step
   - "assisted"   = mostly complete but needs human checkpoints
   - "reference"  = too vague to execute, a human must do it
   List concretely what is missing (e.g. "API endpoint for step 3 not in
   sources", "approval threshold amount unclear"). Do NOT claim
   "executable" if any step lacks a concrete invocation or success
   criterion.
8. Only include facts supported by the source documents. Never invent
   commands, endpoints, or values that are not in the sources — if a detail
   is missing, set the field to null and list it in
   automation_readiness.missing_for_automation.
9. Respond with ONLY the JSON object described below — no prose, no
   markdown fences, no commentary. Omit or use null for step-detail fields
   that do not apply; do not pad them with made-up content.

## OUTPUT SCHEMA

For a one-time project, output exactly:
{"is_skill": false, "reason": "one-time project, not a repeatable workflow"}

For a repeatable workflow, output exactly ONE JSON object with this schema:

{
  "is_skill": true,
  "name": "<concise skill name>",
  "description": "<what this workflow does, when to use it, who runs it>",
  "department": "<engineering|support|operations|sales|hr|general>",
  "roles_involved": ["<role1>", "<role2>"],
  "trigger": {
    "type": "<event|manual|scheduled>",
    "condition": "<what kicks this workflow off>",
    "event_binding": "<machine-readable event if applicable, e.g. 'github:pull_request.opened by dependabot[bot]' — or null>"
  },
  "inputs_schema": {
    "<param_name>": "<description and format, e.g. 'repository in owner/name form'>"
  },
  "is_repeatable": true,
  "steps": [
    {
      "step_order": 1,
      "action": "<short verb-phrase>",
      "details": {
        "explanation": "<human-readable description of this step>",
        "tool": {
          "name": "<specific tool/system, e.g. 'GitHub API'>",
          "method": "<how to invoke, e.g. 'POST /repos/{{input.repo}}/issues'>",
          "auth_required": "<what credentials are needed — or null>"
        },
        "inputs_required": ["<which inputs_schema params this step uses>"],
        "parameters": {"<key>": "<value or template like {{input.repo}}>"},
        "command": "<literal command string if applicable — verbatim from sources — or null>",
        "expected_output": "<what success returns>",
        "success_criteria": "<machine-checkable condition, e.g. 'HTTP 201 returned'>",
        "on_failure": [
          {"if": "<failure condition>", "then": "<action>", "target": "<where, e.g. '#eng-alerts' — or null>"}
        ],
        "branch": {"if": "<condition>", "then": "goto step <N>"},
        "approval_gate": {"if": "<condition>", "require": "<who approves>"}
      },
      "source_document_ids": ["<doc-id>"],
      "source_snippets": ["<verbatim supporting quote>"]
    }
  ],
  "edge_cases": ["<edge-case description>"],
  "conditions": ["<prerequisite / pre-condition>"],
  "prerequisites": ["<what you need before starting>"],
  "automation_readiness": {
    "level": "<executable|assisted|reference>",
    "safe_to_automate": <true|false>,
    "missing_for_automation": ["<concrete gap, e.g. 'API endpoint for step 3 not in sources'>"],
    "requires_human_review": ["<step or decision needing a human>"]
  }
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
        f"First apply the repeatability check: if these documents describe "
        f"a one-time project, return the is_skill:false object. Otherwise "
        f"extract exactly ONE automation-ready skill JSON object following "
        f"the schema in your instructions. Every claim must cite its source "
        f"document(s), and every concrete command, endpoint, or config "
        f"value in the sources must be quoted verbatim in the steps."
    )
