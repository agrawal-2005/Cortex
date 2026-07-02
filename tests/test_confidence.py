import pytest

from backend.knowledge.confidence import ConfidenceScorer


@pytest.fixture
def scorer():
    return ConfidenceScorer()


class TestCalculateConfidence:
    def test_complete_skill_returns_high_score(self, scorer):
        """A fully-populated skill should score at least 0.6 (full completeness)."""
        skill_data = {
            "steps": [
                {"order": 1, "action": "a", "details": "d"},
                {"order": 2, "action": "b", "details": "d"},
                {"order": 3, "action": "c", "details": "d"},
            ],
            "conditions": ["must be on VPN"],
            "edge_cases": ["rollback on failure"],
            "description": "A" * 60,  # >= 50 chars
        }
        score = scorer.calculate_confidence(skill_data, source_count=1)
        # 0.2 (has steps) + 0.1 (3+ steps) + 0.1 (conditions) + 0.1 (edge_cases)
        # + 0.1 (description >= 50 chars) = 0.6
        assert score >= 0.6

    def test_minimal_data_returns_low_score(self, scorer):
        """An empty skill should score 0.0."""
        skill_data = {
            "steps": [],
            "conditions": [],
            "edge_cases": [],
            "description": "",
        }
        score = scorer.calculate_confidence(skill_data, source_count=1)
        assert score == 0.0

    def test_multiple_sources_boost_score(self, scorer):
        """Additional source documents should increase the score."""
        skill_data = {
            "steps": [{"order": 1, "action": "a", "details": "d"}],
            "conditions": [],
            "edge_cases": [],
            "description": "",
        }
        single_source = scorer.calculate_confidence(skill_data, source_count=1)
        multi_source = scorer.calculate_confidence(skill_data, source_count=4)
        assert multi_source > single_source

    def test_source_bonus_capped_at_025(self, scorer):
        """Source bonus should never exceed 0.25 even with many sources."""
        skill_data = {
            "steps": [],
            "conditions": [],
            "edge_cases": [],
            "description": "",
        }
        # source_count = 100 -> (100-1)*0.05 = 4.95 but capped at 0.25
        score = scorer.calculate_confidence(skill_data, source_count=100)
        assert score == pytest.approx(0.25)

    def test_feedback_bonus(self, scorer):
        """Positive feedback entries should increase score."""
        skill_data = {
            "steps": [{"order": 1, "action": "a", "details": "d"}],
            "conditions": [],
            "edge_cases": [],
            "description": "",
        }
        no_feedback = scorer.calculate_confidence(skill_data, source_count=1, feedback_count=0)
        with_feedback = scorer.calculate_confidence(skill_data, source_count=1, feedback_count=3)
        assert with_feedback > no_feedback

    def test_feedback_bonus_capped_at_015(self, scorer):
        """Feedback bonus should never exceed 0.15."""
        skill_data = {
            "steps": [],
            "conditions": [],
            "edge_cases": [],
            "description": "",
        }
        score = scorer.calculate_confidence(skill_data, source_count=1, feedback_count=100)
        assert score == pytest.approx(0.15)

    def test_score_never_exceeds_1(self, scorer):
        """Score should be clamped to a maximum of 1.0."""
        skill_data = {
            "steps": [
                {"order": 1, "action": "a", "details": "d"},
                {"order": 2, "action": "b", "details": "d"},
                {"order": 3, "action": "c", "details": "d"},
            ],
            "conditions": ["c1"],
            "edge_cases": ["e1"],
            "description": "A" * 100,
        }
        score = scorer.calculate_confidence(
            skill_data, source_count=100, feedback_count=100
        )
        assert score <= 1.0


class TestUpdateConfidenceFromFeedback:
    def test_confirmation_increases_score(self, scorer):
        updated = scorer.update_confidence_from_feedback(0.5, "confirmation")
        assert updated == pytest.approx(0.55)

    def test_correction_decreases_score(self, scorer):
        updated = scorer.update_confidence_from_feedback(0.5, "correction")
        assert updated == pytest.approx(0.4)

    def test_rejection_decreases_more(self, scorer):
        updated = scorer.update_confidence_from_feedback(0.5, "rejection")
        assert updated == pytest.approx(0.3)

    def test_rejection_decreases_more_than_correction(self, scorer):
        correction = scorer.update_confidence_from_feedback(0.5, "correction")
        rejection = scorer.update_confidence_from_feedback(0.5, "rejection")
        assert rejection < correction

    def test_confirmation_clamped_at_1(self, scorer):
        updated = scorer.update_confidence_from_feedback(0.98, "confirmation")
        assert updated == 1.0

    def test_correction_floor_at_01(self, scorer):
        """Correction should not drop below 0.1."""
        updated = scorer.update_confidence_from_feedback(0.05, "correction")
        assert updated == pytest.approx(0.1)

    def test_rejection_floor_at_0(self, scorer):
        """Rejection can drop to 0.0."""
        updated = scorer.update_confidence_from_feedback(0.1, "rejection")
        assert updated == 0.0

    def test_unknown_type_returns_unchanged(self, scorer):
        updated = scorer.update_confidence_from_feedback(0.5, "unknown_type")
        assert updated == 0.5
