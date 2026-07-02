"""Confidence scoring for extracted skills."""

from typing import Any


class ConfidenceScorer:
    """Calculates and updates confidence scores for skills based on
    data completeness, source count, and user feedback.
    """

    def calculate_confidence(
        self,
        skill_data: dict[str, Any],
        source_count: int,
        feedback_count: int = 0,
    ) -> float:
        """Calculate a confidence score for a skill.

        Scoring breakdown:
        - Base completeness score (up to 0.6):
            - Has steps with content: +0.2
            - Has conditions: +0.1
            - Has edge cases: +0.1
            - Description length >= 50 chars: +0.1
            - Has 3+ steps: +0.1
        - Source bonus (up to 0.25):
            - Each additional source adds 0.05, capped at 0.25
        - Feedback bonus (up to 0.15):
            - Each positive feedback adds 0.03, capped at 0.15

        Args:
            skill_data: Dict with keys: steps, conditions, edge_cases, description.
            source_count: Number of source documents.
            feedback_count: Number of positive feedback entries.

        Returns:
            Float between 0.0 and 1.0.
        """
        score = 0.0

        # Completeness: steps
        steps = skill_data.get("steps", [])
        if steps and len(steps) > 0:
            score += 0.2
        if len(steps) >= 3:
            score += 0.1

        # Completeness: conditions
        conditions = skill_data.get("conditions", [])
        if conditions and len(conditions) > 0:
            score += 0.1

        # Completeness: edge cases
        edge_cases = skill_data.get("edge_cases", [])
        if edge_cases and len(edge_cases) > 0:
            score += 0.1

        # Completeness: description length
        description = skill_data.get("description", "")
        if len(description) >= 50:
            score += 0.1

        # Source bonus: more sources = higher confidence (capped at 0.25)
        source_bonus = min((source_count - 1) * 0.05, 0.25) if source_count > 1 else 0.0
        score += max(source_bonus, 0.0)

        # Feedback bonus (capped at 0.15)
        feedback_bonus = min(feedback_count * 0.03, 0.15) if feedback_count > 0 else 0.0
        score += feedback_bonus

        return min(max(score, 0.0), 1.0)

    def update_confidence_from_feedback(
        self, current_score: float, feedback_type: str
    ) -> float:
        """Update a confidence score based on user feedback.

        Args:
            current_score: The current confidence score.
            feedback_type: One of "confirmation", "correction", "rejection".

        Returns:
            Updated confidence score, clamped appropriately.
        """
        if feedback_type == "confirmation":
            return min(current_score + 0.05, 1.0)
        elif feedback_type == "correction":
            return max(current_score - 0.1, 0.1)
        elif feedback_type == "rejection":
            return max(current_score - 0.2, 0.0)
        else:
            return current_score
