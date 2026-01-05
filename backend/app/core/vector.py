import asyncio
from app.core.config import settings


from qdrant_client import AsyncQdrantClient

from qdrant_client.http import models as qmodels


class QdrantClientSingleton:
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.client: AsyncQdrantClient | None = None

    @classmethod
    async def get_instance(cls) -> "QdrantClientSingleton":
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance.init()
        return cls._instance

    def init(self):
        if self.client is None:
            self.client = AsyncQdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
            )


async def init_qdrant():
    """
    Call this once at app startup (e.g. in FastAPI's startup event).
    Ensures the Qdrant collection exists. Creates it if it doesn't.
    """
    instance = await QdrantClientSingleton.get_instance()
    qdrant = instance.client
    collections = await qdrant.get_collections()  # pyright: ignore
    existing = [c.name for c in collections.collections]
    assert qdrant
    if "documents" not in existing:
        await qdrant.create_collection(
            collection_name="documents",
            vectors_config=qmodels.VectorParams(
                size=384,
                distance=qmodels.Distance.COSINE,
            ),
            optimizers_config=qmodels.OptimizersConfigDiff(
                indexing_threshold=20000  # optional tuning
            ),
        )
        await qdrant.create_payload_index(
            collection_name="documents",
            field_name="document_id",
            field_schema="keyword",  # pyright: ignore
        )
        print("Created a new collection named Document")
    return instance.client


def get_qdrant() -> AsyncQdrantClient:
    """
    Call this in your service functions after init_qdrant() has run.
    """
    if (
        QdrantClientSingleton._instance is None
        or QdrantClientSingleton._instance.client is None
    ):
        raise ValueError("Qdrant client not initialized. Call init_qdrant() first.")
    return QdrantClientSingleton._instance.client
