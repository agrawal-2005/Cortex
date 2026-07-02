import pytest


DOCUMENT_PAYLOAD = {
    "content": "1. Acknowledge the alert. 2. Triage severity. 3. Escalate if P0.",
    "source_type": "confluence",
    "source_id": "page-ir-001",
    "source_link": "https://wiki.example.com/ir",
    "source_label": "Incident Response Guide",
    "channel_or_project": "sre",
    "author_name": "Jane",
    "author_role": "SRE Lead",
}


@pytest.mark.asyncio
async def test_create_document(client):
    response = await client.post("/api/v1/ingest/documents", json=DOCUMENT_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == DOCUMENT_PAYLOAD["content"]
    assert data["source_type"] == "confluence"
    assert data["source_id"] == "page-ir-001"
    assert data["source_link"] == "https://wiki.example.com/ir"
    assert data["source_label"] == "Incident Response Guide"
    assert data["channel_or_project"] == "sre"
    assert data["author_name"] == "Jane"
    assert data["author_role"] == "SRE Lead"
    assert "id" in data
    assert "ingested_at" in data
    # Verify old fields are NOT present
    assert "title" not in data
    assert "source_url" not in data
    assert "metadata" not in data


@pytest.mark.asyncio
async def test_create_document_minimal(client):
    payload = {
        "content": "Minimal document content.",
        "source_type": "slack",
        "source_id": "msg-999",
    }
    response = await client.post("/api/v1/ingest/documents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Minimal document content."
    assert data["source_type"] == "slack"
    assert data["source_id"] == "msg-999"
    assert data["source_link"] is None
    assert data["source_label"] is None
    assert data["channel_or_project"] is None
    assert data["author_name"] is None
    assert data["author_role"] is None


@pytest.mark.asyncio
async def test_create_documents_batch(client):
    payloads = [
        {
            "content": f"Content for doc {i}",
            "source_type": "slack",
            "source_id": f"msg-{i:03d}",
        }
        for i in range(3)
    ]
    response = await client.post("/api/v1/ingest/batch", json=payloads)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    contents = {d["content"] for d in data}
    assert contents == {"Content for doc 0", "Content for doc 1", "Content for doc 2"}
    # Verify no old fields
    for d in data:
        assert "title" not in d
        assert "source_url" not in d


@pytest.mark.asyncio
async def test_list_documents(client):
    # Create a document first
    await client.post("/api/v1/ingest/documents", json=DOCUMENT_PAYLOAD)

    response = await client.get("/api/v1/ingest/documents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["content"] == DOCUMENT_PAYLOAD["content"]
    assert data[0]["source_type"] == DOCUMENT_PAYLOAD["source_type"]


@pytest.mark.asyncio
async def test_get_document_by_id(client):
    # Create a document
    create_resp = await client.post("/api/v1/ingest/documents", json=DOCUMENT_PAYLOAD)
    doc_id = create_resp.json()["id"]

    # Retrieve it by ID
    response = await client.get(f"/api/v1/ingest/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["content"] == DOCUMENT_PAYLOAD["content"]
    assert data["source_type"] == DOCUMENT_PAYLOAD["source_type"]
    assert data["source_id"] == DOCUMENT_PAYLOAD["source_id"]


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    response = await client.get("/api/v1/ingest/documents/nonexistent-id-000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"
