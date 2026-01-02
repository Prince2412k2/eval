from typing import Dict, List
from fastapi import APIRouter,UploadFile, File
from app.service.chunk_service import SemanticChunker
from app.service.upload_service import DocumentService

upload_router = APIRouter()



@upload_router.post("/")
async def upload_file(file: UploadFile = File(...)):
    out:List[Dict]= await DocumentService.parse(file)
    chunker=SemanticChunker()
    return chunker.chunk_documents(out)
