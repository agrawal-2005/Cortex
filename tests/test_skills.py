import pytest


SKILL_PAYLOAD = {
    "name": "Deploy to production",
    "description": "Steps to deploy the main application to production environment.",
    "department": "engineering",
    "skill_data": {"conditions": ["All tests pass", "Approved by lead"]},
    "steps": [
        {"step_order": 1, "action": "Run tests", "details": {"cmd": "pytest -x"}, "confidence": 0.9},
        {"step_order": 2, "action": "Build image", "details": {"cmd": "docker build ."}, "confidence": 0.8, "depends_on": ["step-1"]},
        {"step_order": 3, "action": "Push to registry", "details": {"cmd": "docker push"}, "confidence": 0.7},
    ],
}


@pytest.mark.asyncio
async def test_list_skills_empty(client):
    response = await client.get("/api/v1/skills/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_create_skill(client):
    response = await client.post("/api/v1/skills/", json=SKILL_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Deploy to production"
    assert data["description"] == SKILL_PAYLOAD["description"]
    assert data["department"] == "engineering"
    assert data["status"] == "draft"
    assert data["confidence"] == 0.0
    assert data["version"] == 1
    assert data["skill_data"] == {"conditions": ["All tests pass", "Approved by lead"]}
    assert "id" in data
    assert "extracted_at" in data
    # Verify old fields are NOT present
    assert "title" not in data
    assert "confidence_score" not in data
    # Verify steps
    assert len(data["steps"]) == 3
    step1 = data["steps"][0]
    assert step1["step_order"] == 1
    assert step1["action"] == "Run tests"
    assert step1["details"] == {"cmd": "pytest -x"}
    assert step1["confidence"] == 0.9
    assert "id" in step1
    assert "skill_id" in step1


@pytest.mark.asyncio
async def test_create_skill_minimal(client):
    payload = {
        "name": "Simple skill",
        "description": "A skill with no steps.",
    }
    response = await client.post("/api/v1/skills/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Simple skill"
    assert data["steps"] == []
    assert data["department"] is None
    assert data["skill_data"] == {}


@pytest.mark.asyncio
async def test_get_skill_by_id(client):
    # Create a skill first
    create_resp = await client.post("/api/v1/skills/", json=SKILL_PAYLOAD)
    skill_id = create_resp.json()["id"]

    # Retrieve it
    response = await client.get(f"/api/v1/skills/{skill_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == skill_id
    assert data["name"] == "Deploy to production"
    assert len(data["steps"]) == 3
    # Steps should be ordered
    orders = [s["step_order"] for s in data["steps"]]
    assert orders == [1, 2, 3]


@pytest.mark.asyncio
async def test_list_skills_after_create(client):
    await client.post("/api/v1/skills/", json=SKILL_PAYLOAD)

    response = await client.get("/api/v1/skills/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Deploy to production"


@pytest.mark.asyncio
async def test_search_skills_empty(client):
    response = await client.get("/api/v1/skills/search", params={"query": "nonexistent"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_search_skills_found(client):
    await client.post("/api/v1/skills/", json=SKILL_PAYLOAD)

    response = await client.get("/api/v1/skills/search", params={"query": "deploy"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert "deploy" in data[0]["name"].lower()


@pytest.mark.asyncio
async def test_get_skill_not_found(client):
    response = await client.get("/api/v1/skills/nonexistent-skill-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"
