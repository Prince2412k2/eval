from groq import AsyncGroq
from app.core.config import settings
from asyncio import Lock


class Groq:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.client = None

    @classmethod
    async def get_instance(cls):
        # Thread-safe singleton init
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance.client = AsyncGroq(api_key=settings.GROQ_API)
                    cls._instance = instance
        return cls._instance


async def init_groq():
    """Initialize the Groq client early (e.g., on app startup)."""
    await Groq.get_instance()


async def get_groq() -> AsyncGroq:
    """Retrieve the shared AsyncGroq client for use in routes."""
    groq = await Groq.get_instance()
    if groq.client is None:
        raise ValueError("Groq client not initialized.")
    return groq.client

