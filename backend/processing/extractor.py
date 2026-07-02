"""Skill extraction from documents using LangChain + HuggingFace Inference API."""

import asyncio
import json
import logging
from typing import Any

from langchain_huggingface import HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.config import settings
from backend.schemas import SkillCreate, SkillStepCreate

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """You are an expert at identifying structured workflows and processes from company documentation.

Analyze the following documents and extract any distinct workflows, processes, or procedures described in them.

For each workflow/process found, provide:
- name: A clear, concise name for the skill/workflow
- description: A detailed description of what this workflow accomplishes
- department: The department this skill belongs to (e.g. "engineering", "support", "operations"), or null if unclear
- steps: An ordered list of steps, each with "step_order" (int starting at 1), "action" (short verb phrase), and "details" (object with additional context, e.g. {{"explanation": "..."}})
- skill_data: An object containing additional structured data:
  - "conditions": A list of prerequisites or conditions that must be met before executing this workflow
  - "edge_cases": A list of edge cases, exceptions, or special scenarios to be aware of
  - "prerequisites": A list of prerequisites needed (tools, access, knowledge)

DOCUMENTS:
{documents}

Return your response as a JSON array of objects. Each object must have exactly these fields:
"name", "description", "department", "steps", "skill_data"

The "steps" field must be an array of objects with "step_order", "action", and "details" fields.
The "skill_data" field must be an object with "conditions", "edge_cases", and "prerequisites" keys (each an array of strings).

If no workflows are found, return an empty array: []

Respond ONLY with valid JSON, no additional text or markdown formatting.

JSON Output:"""


class SkillExtractor:
    """Extracts structured skills/workflows from documents using LLM."""

    def __init__(self) -> None:
        self._llm: HuggingFaceEndpoint | None = None
        self._chain: Any = None

    def _get_llm(self) -> HuggingFaceEndpoint:
        """Lazy-load the HuggingFace LLM endpoint."""
        if self._llm is None:
            self._llm = HuggingFaceEndpoint(
                repo_id=settings.LLM_MODEL,
                huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
                max_new_tokens=2048,
                temperature=0.1,
                repetition_penalty=1.1,
            )
        return self._llm

    def _get_chain(self) -> Any:
        """Build the LangChain extraction chain."""
        if self._chain is None:
            prompt = PromptTemplate(
                input_variables=["documents"],
                template=EXTRACTION_PROMPT_TEMPLATE,
            )
            llm = self._get_llm()
            self._chain = prompt | llm | StrOutputParser()
        return self._chain

    async def extract_skills(
        self, documents: list[dict[str, Any]]
    ) -> list[SkillCreate]:
        """Extract skills from a list of document dicts.

        Args:
            documents: List of dicts with keys: content, source_type, source_id.

        Returns:
            List of SkillCreate objects representing extracted workflows.
        """
        if not documents:
            return []

        # Format documents for the prompt
        formatted_docs = self._format_documents(documents)
        source_ids = [doc.get("source_id", "") for doc in documents if doc.get("source_id")]

        chain = self._get_chain()

        # Retry logic with exponential backoff (3 attempts)
        last_exception: Exception | None = None
        for attempt in range(3):
            try:
                raw_response: str = await chain.ainvoke({"documents": formatted_docs})
                skills = self._parse_response(raw_response, source_ids)
                logger.info(
                    "Extracted %d skills from %d documents", len(skills), len(documents)
                )
                return skills
            except json.JSONDecodeError as exc:
                last_exception = exc
                logger.warning(
                    "JSON parse error on attempt %d/3: %s", attempt + 1, exc
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "Extraction error on attempt %d/3: %s", attempt + 1, exc
                )

            if attempt < 2:
                wait_time = 2 ** attempt  # 1s, 2s
                await asyncio.sleep(wait_time)

        logger.error("Skill extraction failed after 3 attempts: %s", last_exception)
        raise RuntimeError(
            f"Failed to extract skills after 3 attempts: {last_exception}"
        )

    @staticmethod
    def _format_documents(documents: list[dict[str, Any]]) -> str:
        """Format document dicts into a string for the prompt."""
        parts: list[str] = []
        for i, doc in enumerate(documents, 1):
            source_type = doc.get("source_type", "unknown")
            content = doc.get("content", "")
            label = content[:100] if content else "(empty)"
            parts.append(
                f"--- Document {i} ---\n"
                f"Label: {label}\n"
                f"Source: {source_type}\n"
                f"Content:\n{content}\n"
            )
        return "\n".join(parts)

    @staticmethod
    def _parse_response(
        raw_response: str, source_ids: list[str]
    ) -> list[SkillCreate]:
        """Parse the LLM JSON response into SkillCreate objects."""
        # Try to extract JSON from the response
        text = raw_response.strip()

        # Handle cases where LLM wraps JSON in markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (``` markers)
            lines = [
                line for line in lines
                if not line.strip().startswith("```")
            ]
            text = "\n".join(lines).strip()

        # Find the JSON array in the text
        start_idx = text.find("[")
        end_idx = text.rfind("]")
        if start_idx == -1 or end_idx == -1:
            raise json.JSONDecodeError(
                "No JSON array found in response", text, 0
            )

        json_str = text[start_idx : end_idx + 1]
        parsed: list[dict[str, Any]] = json.loads(json_str)

        skills: list[SkillCreate] = []
        for item in parsed:
            # Parse steps into SkillStepCreate objects
            steps = [
                SkillStepCreate(
                    step_order=step.get("step_order", idx + 1),
                    action=step.get("action", ""),
                    details=step.get("details", {}) if isinstance(step.get("details"), dict) else {"explanation": step.get("details", "")},
                    confidence=0.0,
                    depends_on=[],
                )
                for idx, step in enumerate(item.get("steps", []))
            ]

            # Build skill_data from LLM output (conditions, edge_cases, prerequisites)
            raw_skill_data = item.get("skill_data", {})
            if not isinstance(raw_skill_data, dict):
                raw_skill_data = {}
            skill_data = {
                "conditions": raw_skill_data.get("conditions", []),
                "edge_cases": raw_skill_data.get("edge_cases", []),
                "prerequisites": raw_skill_data.get("prerequisites", []),
                "source_document_ids": source_ids,
            }

            skill = SkillCreate(
                name=item.get("name", "Untitled Skill"),
                description=item.get("description", ""),
                department=item.get("department"),
                skill_data=skill_data,
                steps=steps,
            )
            skills.append(skill)

        return skills
