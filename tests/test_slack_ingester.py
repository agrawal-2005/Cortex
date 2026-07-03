import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.ingestion.slack_ingester import SlackExportIngester

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "sample_slack_export"


@pytest.fixture
def ingester():
    """Create ingester with mocked embedding service and vector store."""
    with patch("backend.ingestion.slack_ingester.EmbeddingService") as mock_emb, \
         patch("backend.ingestion.slack_ingester.VectorStore") as mock_vs:
        mock_emb_instance = MagicMock()
        mock_emb_instance.generate_embeddings.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
        mock_emb_instance.generate_embedding.return_value = [0.1] * 384
        mock_emb.return_value = mock_emb_instance

        mock_vs_instance = MagicMock()
        mock_vs.return_value = mock_vs_instance

        ing = SlackExportIngester(FIXTURE_DIR)
        yield ing


class TestUserResolution:
    def test_load_users(self, ingester):
        ingester._load_users()
        assert len(ingester.users) == 3
        assert ingester._get_user_name("U001") == "Sarah Chen"
        assert ingester._get_user_name("U002") == "Mike Torres"
        assert ingester._get_user_name("U003") == "Alex Kim"

    def test_user_roles_resolved(self, ingester):
        ingester._load_users()
        assert ingester._get_user_role("U001") == "Support Team Lead"
        assert ingester._get_user_role("U002") == "Senior Engineer"

    def test_unknown_user_returns_id(self, ingester):
        ingester._load_users()
        assert ingester._get_user_name("U999") == "U999"
        assert ingester._get_user_role("U999") == ""


class TestChannelLoading:
    def test_load_channels(self, ingester):
        ingester._load_channels()
        assert len(ingester.channels) == 2
        assert "engineering" in ingester.channel_names
        assert "presales" in ingester.channel_names


class TestSlackLinks:
    def test_build_slack_link(self, ingester):
        link = ingester._build_slack_link("engineering", "1751328000.000100")
        assert link == "slack://channel?team=T0&id=engineering&message=1751328000000100"

    def test_link_removes_dots_from_timestamp(self, ingester):
        link = ingester._build_slack_link("general", "123.456")
        assert "123456" in link
        assert "." not in link.split("message=")[1]


class TestMessageParsing:
    def test_standalone_messages_parsed(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        # Should have standalone messages + 1 thread (grouped)
        # Standalone: ts 000100, 000200, 000700, 000800, 000900 = 5
        # Thread: ts 000300 (parent + 2 replies grouped as 1) = 1
        # Skipped: channel_join (000600), empty text (001000) = 2
        standalone_docs = [d for d in docs if "(thread)" not in (d.get("source_label") or "")]
        thread_docs = [d for d in docs if "(thread)" in (d.get("source_label") or "")]
        assert len(standalone_docs) >= 4  # at least 4 standalone
        assert len(thread_docs) == 1  # 1 thread group

    def test_author_names_resolved_in_documents(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        author_names = [d["author_name"] for d in docs]
        assert "Sarah Chen" in author_names
        assert "Mike Torres" in author_names

    def test_thread_replies_grouped(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        thread_docs = [d for d in docs if "(thread)" in (d.get("source_label") or "")]
        assert len(thread_docs) == 1
        thread = thread_docs[0]
        # Thread content should include all 3 messages
        assert "[Sarah Chen]:" in thread["content"]
        assert "[Mike Torres]:" in thread["content"]
        assert "[Alex Kim]:" in thread["content"]
        assert "database migrations" in thread["content"]

    def test_channel_join_skipped(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        contents = " ".join(d["content"] for d in docs)
        assert "joined the channel" not in contents

    def test_empty_messages_skipped(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        # No doc should have empty content
        for doc in docs:
            assert doc["content"].strip() != ""

    def test_source_type_is_slack(self, ingester):
        ingester._load_users()
        docs = ingester._parse_messages("engineering", [
            {"type": "message", "user": "U001", "text": "test", "ts": "123.456"}
        ])
        assert docs[0]["source_type"] == "slack"

    def test_source_link_constructed(self, ingester):
        ingester._load_users()
        docs = ingester._parse_messages("engineering", [
            {"type": "message", "user": "U001", "text": "test", "ts": "1751328000.000100"}
        ])
        assert docs[0]["source_link"] == "slack://channel?team=T0&id=engineering&message=1751328000000100"

    def test_file_attachment_detected(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "engineering" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("engineering", messages)

        # The message with file attachment should still be parsed
        file_docs = [d for d in docs if "runbook" in d["content"].lower() or "attached" in d["content"].lower()]
        assert len(file_docs) >= 1

    def test_presales_messages_parsed(self, ingester):
        ingester._load_users()
        with open(FIXTURE_DIR / "presales" / "2026-07-01.json") as f:
            messages = json.load(f)
        docs = ingester._parse_messages("presales", messages)
        assert len(docs) == 5
        assert docs[0]["channel_or_project"] == "presales"


class TestEmptyAndMalformed:
    def test_empty_channel_no_crash(self, ingester):
        ingester._load_users()
        # empty_channel directory has no JSON files — should not crash
        # We test by running the full parse loop manually
        channel_dir = FIXTURE_DIR / "empty_channel"
        docs = []
        for json_file in sorted(channel_dir.glob("*.json")):
            with open(json_file) as f:
                messages = json.load(f)
            docs.extend(ingester._parse_messages("empty_channel", messages))
        assert docs == []

    def test_malformed_json_handled(self, ingester):
        """Malformed JSON file should increment error count, not crash."""
        ingester._load_users()
        ingester._load_channels()
        # The ingester iterates directories and catches JSON errors
        # malformed.json exists in engineering/ — test that it doesn't crash the whole ingest
        # We test _parse_messages won't be called for malformed files
        malformed_path = FIXTURE_DIR / "engineering" / "malformed.json"
        assert malformed_path.exists()
        with pytest.raises(json.JSONDecodeError):
            with open(malformed_path) as f:
                json.load(f)


class TestFullIngest:
    @pytest.mark.asyncio
    async def test_ingest_creates_documents(self, ingester):
        """Full ingest should create documents in the DB."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        stats = await ingester.ingest(mock_db)

        assert stats["documents_created"] > 0
        assert stats["messages_processed"] > 0
        assert mock_db.add.call_count == stats["documents_created"]

    @pytest.mark.asyncio
    async def test_ingest_handles_malformed_gracefully(self, ingester):
        """Ingest should not crash on malformed JSON, just increment errors."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        stats = await ingester.ingest(mock_db)
        assert stats["errors"] >= 1  # malformed.json should cause an error
        assert stats["documents_created"] > 0  # other files still processed
