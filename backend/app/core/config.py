import os
from dotenv import load_dotenv

from app.schema.Enums import Strategy


class Settings:
    def __init__(self) -> None:
        load_dotenv()
        
        self.LLAMA_CLOUD_API_KEY = os.environ.get("LLAMAINDEX")
        self.DB_URL = os.environ.get("DB_URL")
        self.GROQ_API = os.environ.get("GROQ_API")
        self.QDRANT_URL = os.environ.get("QDRANT_URL")
        self.QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
        self.SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        self.SUPABASE_URL = os.environ.get("SUPABASE_URL")
        self.SECRET_KEY = os.environ.get("SECRET_KEY")
        self.GROQ_TRANSCRIPTION_URL: str = (
            "https://api.groq.com/openai/v1/audio/transcriptions"
        )
        self.MAX_AUDIO_SIZE_MB: int = 10
        self.MAX_AUDIO_DURATION_MIN: int = 20

class Defaults:
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    CHUNK_STRATEGY: Strategy = Strategy.SEMANTIC

settings = Settings()  # pyright: ignore
