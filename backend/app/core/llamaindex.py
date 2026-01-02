from asyncio import Lock
from llama_parse import LlamaParse, ResultType
from app.core.config import settings


class LlamaIndex:
    _instance= None
    _lock = Lock()

    def __init__(self):
        self.client = None

    @classmethod
    async def get_instance(cls) :
        # Thread-safe singleton init
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance.client =LlamaParse(result_type=ResultType.MD, verbose=True,api_key=settings.LLAMA_CLOUD_API_KEY)
                    cls._instance = instance
        return cls._instance


async def init_llama():
    """Initialize the Groq client early (e.g., on app startup)."""
    await LlamaIndex.get_instance()




async def get_llama() ->LlamaParse:
    """Retrieve the shared AsyncGroq client for use in routes."""
    llama = await LlamaIndex.get_instance()
    if llama.client is None:
        raise ValueError("Groq client not initialized.")
    return llama.client



