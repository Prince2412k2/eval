from dataclasses import dataclass
import os
from dotenv import load_dotenv

from app.schema.Enums import Strategy


class Settings:
    def __init__(self) -> None:
        load_dotenv()

        self.LLAMA_CLOUD_API_KEY = os.environ.get("LLAMAINDEX", "")
        self.DB_URL = os.environ.get("DB_URL", "")
        self.GROQ_API = os.environ.get("GROQ_API", "")
        self.QDRANT_URL = os.environ.get("QDRANT_URL", "")
        self.QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
        self.SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
        self.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "")


@dataclass
class Defaults:
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CHUNK_STRATEGY: Strategy = Strategy.SEMANTIC

    BUCKET_NAME = "Documents"
    CONTEXT_WINDOW_QUERYLLM = 131072


settings = Settings()  # pyright: ignore
