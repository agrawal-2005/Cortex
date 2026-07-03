import io
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.ingestion.discord_ingester import DiscordIngester

FIXTURE = Path(__file__).parent / "fixtures" / "discord" / "sample_export.json"


@pytest.fixture
def export_data():
    with open(FIXTURE) as f:
        return json.load(f)


@pytest.fixture
def ingester():
    return DiscordIngester(download_attachments=False)


def _api_response(payload, status_code=200, headers=None):
    """Build a mock httpx.Response for live-mode tests."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


# ── Export mode (DiscordChatExporter JSON) ────────────────────────────────


class TestExportParsing:
    @pytest.mark.asyncio
    async def test_document_count(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        # 1001, 1002, 1003 (embed), 1004 (attachment) — 1005 empty and
        # 1006 ThreadCreated are skipped.
        assert len(docs) == 4
        assert ingester.stats["messages"] == 4
        assert ingester.stats["skipped"] == 2

    @pytest.mark.asyncio
    async def test_document_fields(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        doc = docs[0]
        assert doc.source_type == "discord"
        assert doc.source_id == "1001"
        assert doc.source_link == (
            "https://discord.com/channels/111111111111111111/"
            "222222222222222222/1001"
        )
        assert doc.channel_or_project == "engineering"
        assert doc.source_label == "#engineering"
        assert "roll back a bad deploy" in doc.content
        assert isinstance(doc.created_at, datetime)
        assert doc.created_at.year == 2026

    @pytest.mark.asyncio
    async def test_nickname_preferred_over_username(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        assert docs[0].author_name == "Sarah Chen"  # nickname
        assert docs[1].author_name == "mike"        # no nickname → name

    @pytest.mark.asyncio
    async def test_reply_chain_combined(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        reply = next(d for d in docs if d.source_id == "1002")
        assert reply.content.startswith("[Replying to sarah]:")
        assert "roll back a bad deploy" in reply.content       # referenced excerpt
        assert "make rollback" in reply.content                # own content

    @pytest.mark.asyncio
    async def test_bot_message_with_embed(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        bot_doc = next(d for d in docs if d.source_id == "1003")
        assert bot_doc.author_role == "bot"
        assert bot_doc.author_name == "deploybot"
        assert "[Embed: Deploy rolled back — api-server reverted to v2.14.1 by mike]" in bot_doc.content

    @pytest.mark.asyncio
    async def test_attachment_only_message(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        att_doc = next(d for d in docs if d.source_id == "1004")
        assert "[Attachment: runbook.txt]" in att_doc.content
        assert "https://cdn.discordapp.com/attachments" in att_doc.content
        assert ingester.stats["attachments"] == 1

    @pytest.mark.asyncio
    async def test_empty_and_system_messages_skipped(self, ingester, export_data):
        docs = await ingester.parse_export(export_data)
        ids = {d.source_id for d in docs}
        assert "1005" not in ids  # truly empty
        assert "1006" not in ids  # ThreadCreated system message

    @pytest.mark.asyncio
    async def test_invalid_export_raises(self, ingester):
        with pytest.raises(ValueError):
            await ingester.parse_export({"not": "an export"})

    @pytest.mark.asyncio
    async def test_thread_export_counted(self, ingester, export_data):
        export_data["channel"]["type"] = "GuildPublicThread"
        export_data["channel"]["name"] = "incident-2026-05-01"
        docs = await ingester.parse_export(export_data)
        assert ingester.stats["threads"] == 1
        assert docs[0].channel_or_project == "incident-2026-05-01"


class TestAttachmentExtraction:
    @pytest.mark.asyncio
    async def test_text_attachment_downloaded(self):
        ingester = DiscordIngester(download_attachments=True)
        resp = MagicMock()
        resp.content = b"step 1: revert the image tag"
        resp.raise_for_status.return_value = None
        mock_client = AsyncMock()
        mock_client.get.return_value = resp
        mock_client.__aenter__.return_value = mock_client

        with patch("backend.ingestion.discord_ingester.httpx.AsyncClient", return_value=mock_client):
            text = await ingester._attachment_text("runbook.txt", "https://cdn.example/runbook.txt")
        assert text == "step 1: revert the image tag"

    @pytest.mark.asyncio
    async def test_non_text_attachment_ignored(self):
        ingester = DiscordIngester(download_attachments=True)
        text = await ingester._attachment_text("photo.png", "https://cdn.example/photo.png")
        assert text is None

    @pytest.mark.asyncio
    async def test_download_disabled(self):
        ingester = DiscordIngester(download_attachments=False)
        text = await ingester._attachment_text("notes.md", "https://cdn.example/notes.md")
        assert text is None


# ── Live mode (Discord REST API) ──────────────────────────────────────────


def _api_message(msg_id, content, username="sarah", bot=False, msg_type=0, **extra):
    return {
        "id": msg_id,
        "type": msg_type,
        "content": content,
        "timestamp": "2026-05-01T10:00:00.000000+00:00",
        "author": {"id": "9001", "username": username, "bot": bot},
        "attachments": [],
        "embeds": [],
        **extra,
    }


class TestLiveMode:
    @pytest.mark.asyncio
    async def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
        ingester = DiscordIngester(channel_ids=["222"])
        with pytest.raises(ConnectionError):
            await ingester.connect()

    @pytest.mark.asyncio
    async def test_fetch_documents_paginates_with_before(self):
        ingester = DiscordIngester(
            bot_token="x", guild_id="111", channel_ids=["222"],
            max_messages_per_channel=500, download_attachments=False,
        )
        page1 = [_api_message(str(2000 - i), f"message {i}") for i in range(100)]
        page2 = [_api_message("1899", "last message")]
        client = AsyncMock()
        client.get.side_effect = [
            _api_response({"id": "222", "name": "engineering", "guild_id": "111"}),
            _api_response(page1),
            _api_response(page2),
        ]
        ingester._client = client

        docs = await ingester.fetch_documents()
        assert len(docs) == 101

        # Second messages call must pass before=<oldest id of page 1>
        _, kwargs = client.get.call_args_list[2]
        assert kwargs["params"]["before"] == page1[-1]["id"]
        assert docs[0].source_link == "https://discord.com/channels/111/222/2000"
        assert docs[0].channel_or_project == "engineering"

    @pytest.mark.asyncio
    async def test_rate_limit_429_retried(self):
        ingester = DiscordIngester(bot_token="x", channel_ids=["222"])
        limited = _api_response({"retry_after": 0.01}, status_code=429,
                                headers={"Retry-After": "0.01"})
        ok = _api_response({"id": "222", "name": "general"})
        client = AsyncMock()
        client.get.side_effect = [limited, ok]
        ingester._client = client

        resp = await ingester._get("/channels/222")
        assert resp.json()["name"] == "general"
        assert client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_referenced_message_and_bot_flag(self):
        ingester = DiscordIngester(
            bot_token="x", guild_id="111", channel_ids=["222"],
            download_attachments=False,
        )
        messages = [
            _api_message(
                "3002", "agreed, ship it", username="reviewbot", bot=True,
                msg_type=19,
                referenced_message=_api_message("3001", "ready to merge?"),
            ),
            _api_message("3003", "", msg_type=6),  # pinned system msg → skip
        ]
        client = AsyncMock()
        client.get.side_effect = [
            _api_response({"id": "222", "name": "engineering", "guild_id": "111"}),
            _api_response(messages),
        ]
        ingester._client = client

        docs = await ingester.fetch_documents()
        assert len(docs) == 1
        doc = docs[0]
        assert doc.author_role == "bot"
        assert doc.content.startswith("[Replying to sarah]: ready to merge?")
        assert "agreed, ship it" in doc.content

    @pytest.mark.asyncio
    async def test_thread_messages_fetched(self):
        ingester = DiscordIngester(
            bot_token="x", guild_id="111", channel_ids=["222"],
            download_attachments=False,
        )
        starter = _api_message(
            "4001", "incident thread",
            thread={"id": "444", "name": "incident-2026-05-01"},
        )
        thread_msgs = [_api_message("4002", "root cause was a bad config push")]
        client = AsyncMock()
        client.get.side_effect = [
            _api_response({"id": "222", "name": "engineering", "guild_id": "111"}),
            _api_response([starter]),
            _api_response(thread_msgs),
        ]
        ingester._client = client

        docs = await ingester.fetch_documents()
        assert len(docs) == 2
        thread_doc = next(d for d in docs if d.source_id == "4002")
        assert thread_doc.channel_or_project == "engineering / incident-2026-05-01"
        assert ingester.stats["threads"] == 1


# ── API routes ────────────────────────────────────────────────────────────


class TestDiscordRoutes:
    @pytest.mark.asyncio
    async def test_upload_route(self, client):
        with open(FIXTURE, "rb") as f:
            files = {"file": ("export.json", f, "application/json")}
            response = await client.post("/api/ingest/discord/upload", files=files)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["documents_ingested"] == 4

        # Documents actually landed in the DB
        listing = await client.get("/api/v1/ingest/documents", params={"limit": 10})
        docs = listing.json()
        discord_docs = [d for d in docs if d["source_type"] == "discord"]
        assert len(discord_docs) == 4

    @pytest.mark.asyncio
    async def test_upload_rejects_non_json(self, client):
        files = {"file": ("export.csv", io.BytesIO(b"a,b"), "text/csv")}
        response = await client.post("/api/ingest/discord/upload", files=files)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_rejects_bad_structure(self, client):
        files = {"file": ("export.json", io.BytesIO(b'{"foo": 1}'), "application/json")}
        response = await client.post("/api/ingest/discord/upload", files=files)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_live_route_requires_token(self, client, monkeypatch):
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
        response = await client.post(
            "/api/ingest/discord/live",
            json={"guild_id": "111", "channel_ids": ["222"]},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_live_route_with_mocked_ingester(self, client):
        from backend.schemas import DocumentCreate

        mock_ingester = MagicMock()
        mock_ingester.bot_token = "x"
        mock_ingester.stats = {"messages": 1}
        mock_ingester.ingest = AsyncMock(return_value=[
            DocumentCreate(
                content="hello from discord",
                source_type="discord",
                source_id="5001",
                source_link="https://discord.com/channels/111/222/5001",
                channel_or_project="general",
                author_name="sarah",
            )
        ])
        with patch("backend.api.routes_ingest.DiscordIngester", return_value=mock_ingester):
            response = await client.post(
                "/api/ingest/discord/live",
                json={"guild_id": "111", "channel_ids": ["222"], "bot_token": "x"},
            )
        assert response.status_code == 200
        result = response.json()
        assert result["documents_ingested"] == 1
        assert result["stats"] == {"messages": 1}
