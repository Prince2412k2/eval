from enum import Enum
from typing import Optional
from pydantic import BaseModel


class FileStage(str, Enum):
    """Processing stages for file upload"""
    HASHING = "hashing"
    UPLOADING = "uploading"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    UPDATING = "updating"
    FINISHED = "finished"


class FileStatus(str, Enum):
    """Status of file processing"""
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class UploadProgress(BaseModel):
    """Progress update for file upload"""
    filename: str
    stage: FileStage
    status: FileStatus
    message: Optional[str] = None
    hash: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    chunk_count: Optional[int] = None
    error: Optional[str] = None
