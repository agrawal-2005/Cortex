import logging
from typing import Any

import httpx

from backend.ingestion.base import BaseConnector
from backend.schemas import DocumentCreate

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"


class SlackConnector(BaseConnector):
    """Connector that ingests messages from Slack channels."""

    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self._client: httpx.AsyncClient | None = None
        self._headers: dict[str, str] = {
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        """Create an httpx async client and verify auth."""
        self._client = httpx.AsyncClient(
            base_url=SLACK_API_BASE,
            headers=self._headers,
            timeout=30.0,
        )
        response = await self._client.post("/auth.test")
        data = response.json()
        if not data.get("ok"):
            raise ConnectionError(
                f"Slack auth failed: {data.get('error', 'unknown error')}"
            )
        logger.info("Slack auth successful for team: %s", data.get("team"))

    async def _list_channels(self) -> list[dict[str, Any]]:
        """Fetch all public channels the bot has access to."""
        assert self._client is not None, "Call connect() first"
        channels: list[dict[str, Any]] = []
        cursor: str | None = None

        while True:
            params: dict[str, Any] = {
                "types": "public_channel",
                "limit": 200,
            }
            if cursor:
                params["cursor"] = cursor

            response = await self._client.get(
                "/conversations.list", params=params
            )
            data = response.json()
            if not data.get("ok"):
                logger.error("Failed to list channels: %s", data.get("error"))
                break

            channels.extend(data.get("channels", []))
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return channels

    async def _fetch_channel_history(
        self, channel_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch recent messages from a single channel."""
        assert self._client is not None, "Call connect() first"

        try:
            response = await self._client.get(
                "/conversations.history",
                params={"channel": channel_id, "limit": limit},
            )
            data = response.json()
            if not data.get("ok"):
                logger.error(
                    "Failed to fetch history for %s: %s",
                    channel_id,
                    data.get("error"),
                )
                return []
            return data.get("messages", [])
        except httpx.HTTPError as exc:
            logger.error(
                "HTTP error fetching history for %s: %s", channel_id, exc
            )
            return []

    async def fetch_documents(self) -> list[DocumentCreate]:
        """Fetch messages from all accessible channels and convert to documents."""
        channels = await self._list_channels()
        documents: list[DocumentCreate] = []

        for channel in channels:
            channel_id: str = channel["id"]
            channel_name: str = channel.get("name", channel_id)
            messages = await self._fetch_channel_history(channel_id)

            for msg in messages:
                text = msg.get("text", "").strip()
                if not text:
                    continue

                ts = msg.get("ts", "")
                user = msg.get("user", "unknown")

                documents.append(
                    DocumentCreate(
                        title=f"Slack message in #{channel_name}",
                        content=text,
                        source_type="slack",
                        source_id=f"{channel_id}:{ts}",
                        source_url=None,
                        metadata={
                            "channel_id": channel_id,
                            "channel_name": channel_name,
                            "user": user,
                            "ts": ts,
                        },
                    )
                )

        logger.info(
            "Fetched %d documents from %d Slack channels",
            len(documents),
            len(channels),
        )
        return documents

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
