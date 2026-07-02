from abc import ABC, abstractmethod

from backend.schemas import DocumentCreate


class BaseConnector(ABC):
    """Abstract base class for all data source connectors."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the data source."""
        ...

    @abstractmethod
    async def fetch_documents(self) -> list[DocumentCreate]:
        """Fetch documents from the connected data source."""
        ...

    async def ingest(self) -> list[DocumentCreate]:
        """Connect to the source, fetch documents, and return them."""
        await self.connect()
        documents = await self.fetch_documents()
        return documents
