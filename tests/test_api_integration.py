import pytest


@pytest.mark.asyncio
async def test_ingest_file_csv(client):
    """POST /api/ingest/file - upload CSV, verify documents created."""
    csv_content = "content,source_id,author_name\nHow to deploy to prod,deploy-1,John\nHow to rollback,rollback-1,Jane"

    import io
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    data = {"source_type": "custom"}

    response = await client.post("/api/ingest/file", files=files, data=data)
    assert response.status_code == 200
    result = response.json()
    assert result["documents_created"] == 2
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_ingest_file_bad_format(client):
    """POST /api/ingest/file - reject non-csv/json files."""
    import io
    files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    data = {"source_type": "custom"}

    response = await client.post("/api/ingest/file", files=files, data=data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_skills_empty(client):
    """GET /api/skills/ - empty list initially."""
    response = await client.get("/api/skills/")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_create_and_list_skills(client):
    """Create a skill via v1 API, then list via v2 API."""
    # Create via v1
    skill_data = {
        "name": "Test Skill",
        "description": "A test skill for integration testing",
        "department": "engineering",
        "skill_data": {"conditions": ["Test condition"]},
        "steps": [
            {"step_order": 1, "action": "Do something", "details": {"explanation": "test"}, "confidence": 0.9}
        ]
    }
    create_res = await client.post("/api/v1/skills/", json=skill_data)
    assert create_res.status_code == 201
    assert create_res.json()["id"]

    # List via v2
    list_res = await client.get("/api/skills/")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Test Skill"
    assert items[0]["step_count"] == 1


@pytest.mark.asyncio
async def test_list_skills_filter_by_status(client):
    """GET /api/skills/?status=draft - filters work."""
    # Create a skill (defaults to draft)
    await client.post("/api/v1/skills/", json={
        "name": "Draft Skill", "description": "test", "steps": []
    })

    # Filter by draft
    res = await client.get("/api/skills/?status=draft")
    assert res.status_code == 200
    assert res.json()["total"] >= 1

    # Filter by verified (should be 0)
    res = await client.get("/api/skills/?status=verified")
    assert res.status_code == 200
    assert res.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_skills_filter_by_department(client):
    """GET /api/skills/?department=engineering - filters by department."""
    await client.post("/api/v1/skills/", json={
        "name": "Eng Skill", "description": "test", "department": "engineering", "steps": []
    })
    await client.post("/api/v1/skills/", json={
        "name": "Support Skill", "description": "test", "department": "support", "steps": []
    })

    res = await client.get("/api/skills/?department=engineering")
    assert res.status_code == 200
    items = res.json()["items"]
    assert all(i["department"] == "engineering" for i in items)


@pytest.mark.asyncio
async def test_get_skill_detail(client):
    """GET /api/skills/{id} - returns full skill with steps."""
    create_res = await client.post("/api/v1/skills/", json={
        "name": "Detail Skill", "description": "Full detail test",
        "department": "support",
        "skill_data": {"edge_cases": ["Edge case 1"], "prerequisites": ["Access"]},
        "steps": [
            {"step_order": 1, "action": "Step one", "details": {"explanation": "Do this"}, "confidence": 0.9},
            {"step_order": 2, "action": "Step two", "details": {"explanation": "Then this"}, "confidence": 0.8}
        ]
    })
    skill_id = create_res.json()["id"]

    res = await client.get(f"/api/skills/{skill_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Detail Skill"
    assert len(data["steps"]) == 2
    assert "markdown" in data  # should include rendered markdown


@pytest.mark.asyncio
async def test_get_skill_executable(client):
    """GET /api/skills/{id}/executable - machine-readable format."""
    create_res = await client.post("/api/v1/skills/", json={
        "name": "Executable Skill", "description": "For AI agents",
        "skill_data": {"prerequisites": ["API key"], "roles_involved": ["Engineer"]},
        "steps": [{"step_order": 1, "action": "Call API", "details": {"tools": ["curl"]}, "confidence": 0.95}]
    })
    skill_id = create_res.json()["id"]

    res = await client.get(f"/api/skills/{skill_id}/executable")
    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == "1.0"
    assert data["skill_id"] == skill_id
    assert len(data["execution_plan"]) == 1
    assert data["execution_plan"][0]["action"] == "Call API"
    assert "curl" in data["execution_plan"][0]["tools"]


@pytest.mark.asyncio
async def test_get_skill_not_found(client):
    """GET /api/skills/{bad_id} - returns 404."""
    res = await client.get("/api/skills/nonexistent-id")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_submit_feedback(client):
    """POST /api/feedback/ - submit feedback on a skill."""
    create_res = await client.post("/api/v1/skills/", json={
        "name": "Feedback Target", "description": "test", "steps": []
    })
    skill_id = create_res.json()["id"]

    fb_res = await client.post("/api/feedback/", json={
        "skill_id": skill_id,
        "action": "approve",
        "submitted_by": "Test User"
    })
    assert fb_res.status_code == 201
    data = fb_res.json()
    assert data["action"] == "approve"
    assert data["submitted_by"] == "Test User"


@pytest.mark.asyncio
async def test_feedback_history(client):
    """GET /api/feedback/history/{skill_id} - returns feedback list."""
    create_res = await client.post("/api/v1/skills/", json={
        "name": "History Target", "description": "test", "steps": []
    })
    skill_id = create_res.json()["id"]

    # Submit two feedbacks
    await client.post("/api/feedback/", json={"skill_id": skill_id, "action": "approve", "submitted_by": "User1"})
    await client.post("/api/feedback/", json={"skill_id": skill_id, "action": "edit", "reason": "Fix step 2", "submitted_by": "User2"})

    res = await client.get(f"/api/feedback/history/{skill_id}")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 2


@pytest.mark.asyncio
async def test_feedback_on_nonexistent_skill(client):
    """POST /api/feedback/ - 404 for bad skill_id."""
    res = await client.post("/api/feedback/", json={
        "skill_id": "nonexistent",
        "action": "approve"
    })
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_query_no_results(client):
    """POST /api/query/ - returns no-match message when empty DB."""
    res = await client.post("/api/query/", json={"question": "How do we deploy?"})
    assert res.status_code == 200
    data = res.json()
    assert data["skill"] is None
    answer = data["readable_answer"].lower()
    assert any(phrase in answer for phrase in [
        "don't have enough knowledge",
        "no matching",
        "no extracted skill",
        "found related documents",
    ])


@pytest.mark.asyncio
async def test_query_empty_question(client):
    """POST /api/query/ - 400 for empty question."""
    res = await client.post("/api/query/", json={"question": ""})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health - returns healthy status."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
