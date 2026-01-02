from supabase import acreate_client, AsyncClient
from app.core.config import settings
from asyncio import Lock


class SupaBase:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self.client = None

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance.client = await acreate_client(
                        settings.SUPABASE_URL, settings.SUPABASE_KEY
                    )
                    cls._instance = instance
        return cls._instance


async def init_supabase():
    """Initialize the Groq client early (e.g., on app startup)."""
    await SupaBase.get_instance()


async def get_supabase() -> AsyncClient:
    """Retrieve the shared AsyncGroq client for use in routes."""
    groq = await SupaBase.get_instance()
    if groq.client is None:
        raise ValueError("Groq client not initialized.")
    return groq.client
