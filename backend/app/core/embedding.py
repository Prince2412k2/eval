from fastembed import TextEmbedding
from asyncio import Lock


class EmbbedModel:
    _instance = None
    _lock = Lock()

    def __init__(self) -> None:
        self.embed_model = None

    def init(self):
        if self.embed_model is None:
            self.embed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

    @classmethod
    async def get_instance(cls):
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance.model = TextEmbedding()  # pyright: ignore
                    cls._instance = instance
        return cls._instance


embbed_model = EmbbedModel()


def get_embbed() -> TextEmbedding:
    if embbed_model.embed_model is None:
        raise ValueError("embed_model not initialized")
    return embbed_model.embed_model
