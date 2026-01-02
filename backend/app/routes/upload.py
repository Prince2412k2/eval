from fastapi import APIRouter, Depends,UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.service.upload_service import DocumentCRUD, DocumentCreate, SupabaseFileCRUD
from app.core.database import get_db
from sqlalchemy.exc import IntegrityError

upload_router = APIRouter()



@upload_router.post("/")
async def upload_file(file: UploadFile = File(...),db:AsyncSession=Depends(get_db)):
    try:
        file_hash=await SupabaseFileCRUD._hash_bytes(file)
        data=DocumentCreate(mime_type=file.content_type if file.content_type else ""
                            ,title=file.filename if file.filename else "Untitled")
        doc=await DocumentCRUD.create(db,data,file_hash)
        print("Document created with ID:", doc)
        out=await SupabaseFileCRUD.create(file,file_hash)
        return {"message":"File uploaded successfully","file":out}
    except IntegrityError:
        return {"error":"File already exists"}
    except Exception as e:
        return {"error":str(e)}

    # parsed_docs:List[Dict]= await DocumentService.parse(file)
    # chunker=ChunkerFactory.get_chunker(Defaults.CHUNK_STRATEGY)
    # chunks= chunker.chunk_documents(parsed_docs)


    
