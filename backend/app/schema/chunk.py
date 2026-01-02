
from typing import Dict
from pydantic import BaseModel


class Chunk(BaseModel):
    text: str
    page: int
    chunk_index: int
    metadata: Dict
