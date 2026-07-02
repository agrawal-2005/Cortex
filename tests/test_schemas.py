import pytest
from pydantic import ValidationError

from backend.schemas import (
    DocumentCreate,
    SkillStepCreate,
    SkillCreate,
    FeedbackCreate,
)


class TestDocumentCreate:
    def test_valid_data(self):
        doc = DocumentCreate(
            content="Step 1: do this. Step 2: do that.",
            source_type="notion",
            source_id="page-123",
            source_link="https://notion.so/page-123",
            source_label="Onboarding Guide",
            channel_or_project="engineering",
            author_name="Alice",
            author_role="engineer",
        )
        assert doc.content == "Step 1: do this. Step 2: do that."
        assert doc.source_type == "notion"
        assert doc.source_id == "page-123"
        assert doc.source_link == "https://notion.so/page-123"
        assert doc.source_label == "Onboarding Guide"
        assert doc.channel_or_project == "engineering"
        assert doc.author_name == "Alice"
        assert doc.author_role == "engineer"

    def test_defaults(self):
        doc = DocumentCreate(
            content="Some content",
            source_type="slack",
            source_id="msg-001",
        )
        assert doc.source_link is None
        assert doc.source_label is None
        assert doc.channel_or_project is None
        assert doc.author_name is None
        assert doc.author_role is None
        assert doc.created_at is None
        assert doc.embedding_id is None

    def test_missing_content_raises(self):
        with pytest.raises(ValidationError):
            DocumentCreate(
                source_type="slack",
                source_id="msg-002",
            )

    def test_missing_source_type_raises(self):
        with pytest.raises(ValidationError):
            DocumentCreate(
                content="Some content",
                source_id="msg-002",
            )

    def test_missing_source_id_raises(self):
        with pytest.raises(ValidationError):
            DocumentCreate(
                content="Some content",
                source_type="slack",
            )


class TestSkillStepCreate:
    def test_valid_data(self):
        step = SkillStepCreate(
            step_order=1,
            action="Open dashboard",
            details={"url": "/dashboard"},
            confidence=0.8,
            depends_on=["step-0"],
        )
        assert step.step_order == 1
        assert step.action == "Open dashboard"
        assert step.details == {"url": "/dashboard"}
        assert step.confidence == 0.8
        assert step.depends_on == ["step-0"]

    def test_defaults(self):
        step = SkillStepCreate(step_order=1, action="Do something")
        assert step.details == {}
        assert step.confidence == 0.0
        assert step.depends_on == []

    def test_missing_step_order_raises(self):
        with pytest.raises(ValidationError):
            SkillStepCreate(action="Do something")

    def test_missing_action_raises(self):
        with pytest.raises(ValidationError):
            SkillStepCreate(step_order=1)


class TestSkillCreate:
    def test_valid_data(self):
        skill = SkillCreate(
            name="Deploy to production",
            description="Steps to deploy the main app to production.",
            department="engineering",
            skill_data={"conditions": ["All tests pass"]},
            steps=[
                SkillStepCreate(step_order=1, action="Run tests", details={"cmd": "pytest -x"}),
                SkillStepCreate(step_order=2, action="Build image", details={"cmd": "docker build ."}),
            ],
        )
        assert skill.name == "Deploy to production"
        assert skill.description == "Steps to deploy the main app to production."
        assert skill.department == "engineering"
        assert len(skill.steps) == 2
        assert skill.skill_data == {"conditions": ["All tests pass"]}

    def test_defaults(self):
        skill = SkillCreate(
            name="Minimal skill",
            description="A minimal skill with defaults.",
        )
        assert skill.steps == []
        assert skill.department is None
        assert skill.skill_data == {}

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            SkillCreate(description="No name provided.")

    def test_missing_description_raises(self):
        with pytest.raises(ValidationError):
            SkillCreate(name="No description")


class TestFeedbackCreate:
    def test_valid_approve(self):
        fb = FeedbackCreate(
            skill_id="skill-abc",
            action="approve",
        )
        assert fb.skill_id == "skill-abc"
        assert fb.action == "approve"
        assert fb.step_id is None
        assert fb.original_content is None
        assert fb.corrected_content is None
        assert fb.reason is None
        assert fb.submitted_by is None

    def test_valid_edit(self):
        fb = FeedbackCreate(
            skill_id="skill-abc",
            step_id="step-1",
            action="edit",
            original_content="old text",
            corrected_content="new text",
            reason="Typo fix",
            submitted_by="alice",
        )
        assert fb.action == "edit"
        assert fb.step_id == "step-1"
        assert fb.original_content == "old text"
        assert fb.corrected_content == "new text"
        assert fb.reason == "Typo fix"
        assert fb.submitted_by == "alice"

    def test_valid_reject(self):
        fb = FeedbackCreate(
            skill_id="skill-xyz",
            action="reject",
            reason="Completely wrong procedure",
        )
        assert fb.action == "reject"
        assert fb.reason == "Completely wrong procedure"

    def test_missing_skill_id_raises(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(action="approve")

    def test_missing_action_raises(self):
        with pytest.raises(ValidationError):
            FeedbackCreate(skill_id="skill-abc")
