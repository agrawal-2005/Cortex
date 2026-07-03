"""Discord ingester.

Two input modes:

1. Live mode — plain HTTP against the Discord REST API (v10) with a bot
   token (from the DISCORD_BOT_TOKEN env var or passed explicitly).
   Paginates channel messages with the ``before`` parameter and respects
   X-RateLimit headers.

2. Export mode — parses JSON files produced by DiscordChatExporter
   (https://github.com/Tyrrrz/DiscordChatExporter), shaped as
   ``{"guild": {...}, "channel": {...}, "messages": [...]}``.

Both modes normalize messages into a common shape and convert them to
Cortex ``DocumentCreate`` records with ``source_type="discord"``.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.ingestion.base import BaseConnector
from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10"

# Message types worth ingesting. Everything else (pins, joins,
# boosts, "thread created" markers, ...) is system noise.
API_MESSAGE_TYPES = {0, 19, 21}  # DEFAULT, REPLY, THREAD_STARTER_MESSAGE
EXPORT_MESSAGE_TYPES = {"Default", "Reply", "ThreadStarterMessage"}

TEXT_ATTACHMENT_EXTENSIONS = (".txt", ".md", ".csv")
MAX_ATTACHMENT_BYTES = 512 * 1024
REPLY_EXCERPT_LEN = 200


class DiscordIngester(BaseConnector):
    """Ingests Discord messages from the live API or a DiscordChatExporter dump."""

    def __init__(
        self,
        bot_token: str | None = None,
        guild_id: str | None = None,
        channel_ids: list[str] | None = None,
        max_messages_per_channel: int = 1000,
        download_attachments: bool = True,
    ) -> None:
        """
        Args:
            bot_token: Discord bot token (falls back to DISCORD_BOT_TOKEN
                env var). Only required for live mode.
            guild_id: Guild (server) ID — used to build message links.
            channel_ids: Channels to pull in live mode.
            max_messages_per_channel: Pagination cap per channel/thread.
            download_attachments: Download and inline text from
                .txt/.md/.csv attachments (requires network access).
        """
        self.bot_token = bot_token or os.environ.get("DISCORD_BOT_TOKEN")
        self.guild_id = guild_id
        self.channel_ids = channel_ids or []
        self.max_messages_per_channel = max_messages_per_channel
        self.download_attachments = download_attachments
        self._client: httpx.AsyncClient | None = None
        self.stats = {
            "messages": 0,
            "threads": 0,
            "attachments": 0,
            "skipped": 0,
            "channels": 0,
        }

    # ── Live mode (Discord REST API) ─────────────────────────────────────

    async def connect(self) -> None:
        """Create the HTTP client and verify the bot token."""
        if not self.bot_token:
            raise ConnectionError(
                "No Discord bot token: pass bot_token or set DISCORD_BOT_TOKEN"
            )
        self._client = httpx.AsyncClient(
            base_url=DISCORD_API_BASE,
            headers={
                "Authorization": f"Bot {self.bot_token}",
                "User-Agent": "cortex-ingester",
            },
            timeout=30.0,
        )
        resp = await self._get("/users/@me")
        me = resp.json()
        logger.info("Connected to Discord as bot %s", me.get("username"))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """GET with Discord rate-limit handling (X-RateLimit headers, 429)."""
        assert self._client is not None, "Call connect() first"
        while True:
            resp = await self._client.get(path, params=params)
            if resp.status_code == 429:
                try:
                    retry_after = float(
                        resp.headers.get("Retry-After")
                        or resp.json().get("retry_after", 1.0)
                    )
                except (ValueError, KeyError):
                    retry_after = 1.0
                logger.warning("Discord rate limited; sleeping %.2fs", retry_after)
                await asyncio.sleep(retry_after)
                continue
            resp.raise_for_status()
            # Pre-emptively wait when the bucket is drained.
            if resp.headers.get("X-RateLimit-Remaining") == "0":
                reset_after = float(resp.headers.get("X-RateLimit-Reset-After", "1"))
                logger.debug("Rate limit bucket empty; sleeping %.2fs", reset_after)
                await asyncio.sleep(reset_after)
            return resp

    async def _fetch_channel_messages(self, channel_id: str) -> list[dict[str, Any]]:
        """Paginate a channel's messages (newest first) via ``before``."""
        messages: list[dict[str, Any]] = []
        before: str | None = None
        while len(messages) < self.max_messages_per_channel:
            params: dict[str, Any] = {"limit": 100}
            if before:
                params["before"] = before
            resp = await self._get(f"/channels/{channel_id}/messages", params=params)
            batch = resp.json()
            if not batch:
                break
            messages.extend(batch)
            before = batch[-1]["id"]
            if len(batch) < 100:
                break
        return messages[: self.max_messages_per_channel]

    async def fetch_documents(self) -> list[DocumentCreate]:
        """Live mode: fetch messages from all configured channels."""
        if not self.channel_ids:
            raise ValueError("Live mode requires channel_ids")
        documents: list[DocumentCreate] = []
        for channel_id in self.channel_ids:
            resp = await self._get(f"/channels/{channel_id}")
            channel = resp.json()
            channel_name = channel.get("name", channel_id)
            guild_id = self.guild_id or channel.get("guild_id", "@me")
            self.stats["channels"] += 1

            messages = await self._fetch_channel_messages(channel_id)
            for msg in messages:
                doc = await self._build_document(
                    self._normalize_api_message(msg, guild_id, channel_id, channel_name)
                )
                if doc:
                    documents.append(doc)

                # Messages that started a thread carry a `thread` object;
                # a thread is itself a channel, so paginate it the same way.
                thread = msg.get("thread")
                if thread and thread.get("id"):
                    documents.extend(
                        await self._fetch_thread(thread, guild_id, channel_name)
                    )
        logger.info("Discord live ingestion complete: %s", self.stats)
        return documents

    async def _fetch_thread(
        self, thread: dict[str, Any], guild_id: str, parent_channel_name: str
    ) -> list[DocumentCreate]:
        thread_id = thread["id"]
        thread_label = f"{parent_channel_name} / {thread.get('name', thread_id)}"
        docs: list[DocumentCreate] = []
        for msg in await self._fetch_channel_messages(thread_id):
            doc = await self._build_document(
                self._normalize_api_message(msg, guild_id, thread_id, thread_label)
            )
            if doc:
                docs.append(doc)
        if docs:
            self.stats["threads"] += 1
        return docs

    # ── Export mode (DiscordChatExporter JSON) ───────────────────────────

    async def parse_export(self, data: dict[str, Any]) -> list[DocumentCreate]:
        """Parse a DiscordChatExporter JSON export into documents."""
        if not isinstance(data, dict) or "messages" not in data:
            raise ValueError(
                "Invalid DiscordChatExporter export: expected an object with "
                "'guild', 'channel', and 'messages' keys."
            )
        guild = data.get("guild") or {}
        channel = data.get("channel") or {}
        messages = data["messages"]
        by_id = {m.get("id"): m for m in messages if isinstance(m, dict)}
        self.stats["channels"] += 1
        if "Thread" in (channel.get("type") or ""):
            self.stats["threads"] += 1

        documents: list[DocumentCreate] = []
        for msg in messages:
            doc = await self._build_document(
                self._normalize_export_message(msg, guild, channel, by_id)
            )
            if doc:
                documents.append(doc)
        logger.info("Discord export ingestion complete: %s", self.stats)
        return documents

    # ── Normalization ────────────────────────────────────────────────────

    def _normalize_api_message(
        self,
        msg: dict[str, Any],
        guild_id: str,
        channel_id: str,
        channel_name: str,
    ) -> dict[str, Any] | None:
        if msg.get("type") not in API_MESSAGE_TYPES:
            return None
        author = msg.get("author") or {}
        reply_to = None
        ref = msg.get("referenced_message")
        if ref:
            ref_author = (ref.get("author") or {}).get("username", "unknown")
            reply_to = {"author": ref_author, "content": ref.get("content") or ""}
        return {
            "id": msg.get("id", ""),
            "content": msg.get("content") or "",
            "author_name": author.get("username"),
            "is_bot": bool(author.get("bot")),
            "timestamp": msg.get("timestamp"),
            "attachments": [
                {"filename": a.get("filename", ""), "url": a.get("url", "")}
                for a in msg.get("attachments") or []
            ],
            "embeds": msg.get("embeds") or [],
            "reply_to": reply_to,
            "guild_id": guild_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
        }

    def _normalize_export_message(
        self,
        msg: dict[str, Any],
        guild: dict[str, Any],
        channel: dict[str, Any],
        by_id: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        if msg.get("type") not in EXPORT_MESSAGE_TYPES:
            return None
        author = msg.get("author") or {}
        reply_to = None
        ref = msg.get("reference")
        if ref and ref.get("messageId"):
            ref_msg = by_id.get(ref["messageId"])
            if ref_msg:
                ref_author = (ref_msg.get("author") or {}).get("name", "unknown")
                reply_to = {
                    "author": ref_author,
                    "content": ref_msg.get("content") or "",
                }
        return {
            "id": msg.get("id", ""),
            "content": msg.get("content") or "",
            "author_name": author.get("nickname") or author.get("name"),
            "is_bot": bool(author.get("isBot")),
            "timestamp": msg.get("timestamp"),
            "attachments": [
                {"filename": a.get("fileName", ""), "url": a.get("url", "")}
                for a in msg.get("attachments") or []
            ],
            "embeds": msg.get("embeds") or [],
            "reply_to": reply_to,
            "guild_id": guild.get("id", "@me"),
            "channel_id": channel.get("id", ""),
            "channel_name": channel.get("name", "unknown"),
        }

    # ── Document building ────────────────────────────────────────────────

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        # DB column is TIMESTAMP WITHOUT TIME ZONE — store naive UTC.
        return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt

    async def _attachment_text(self, filename: str, url: str) -> str | None:
        """Download and return text for .txt/.md/.csv attachments."""
        if not self.download_attachments or not url:
            return None
        if not filename.lower().endswith(TEXT_ATTACHMENT_EXTENSIONS):
            return None
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                if len(resp.content) > MAX_ATTACHMENT_BYTES:
                    return None
                return resp.content.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning("Failed to fetch attachment %s: %s", filename, e)
            return None

    async def _build_document(
        self, norm: dict[str, Any] | None
    ) -> DocumentCreate | None:
        """Convert a normalized message into a DocumentCreate, or None to skip."""
        if norm is None:
            self.stats["skipped"] += 1
            return None

        parts: list[str] = []

        reply = norm["reply_to"]
        if reply and reply["content"]:
            excerpt = reply["content"][:REPLY_EXCERPT_LEN]
            parts.append(f"[Replying to {reply['author']}]: {excerpt}")

        if norm["content"].strip():
            parts.append(norm["content"].strip())

        for embed in norm["embeds"]:
            title = (embed.get("title") or "").strip()
            description = (embed.get("description") or "").strip()
            embed_text = " — ".join(p for p in (title, description) if p)
            if embed_text:
                parts.append(f"[Embed: {embed_text}]")

        for att in norm["attachments"]:
            filename, url = att["filename"], att["url"]
            parts.append(f"[Attachment: {filename}] ({url})")
            self.stats["attachments"] += 1
            text = await self._attachment_text(filename, url)
            if text:
                parts.append(text.strip())

        if not parts:
            # Truly empty message (no text, embeds, or attachments)
            self.stats["skipped"] += 1
            return None

        link = (
            f"https://discord.com/channels/"
            f"{norm['guild_id']}/{norm['channel_id']}/{norm['id']}"
        )
        self.stats["messages"] += 1
        return DocumentCreate(
            content="\n\n".join(parts),
            source_type="discord",
            source_id=norm["id"],
            source_link=link,
            source_label=f"#{norm['channel_name']}",
            channel_or_project=norm["channel_name"],
            author_name=norm["author_name"],
            author_role="bot" if norm["is_bot"] else None,
            created_at=self._parse_timestamp(norm["timestamp"]),
        )

    async def ingest(self) -> list[DocumentCreate]:
        try:
            return await super().ingest()
        finally:
            await self.close()
