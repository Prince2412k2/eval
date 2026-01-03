from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.embedding import embbed_model
from app.core.database import init_db
from app.core.groq import init_groq
from app.core.vector import init_qdrant

# from app.core.groq import init_groq
from app.core.supabase import init_supabase
from fastapi.middleware.cors import CORSMiddleware
from app.core.llamaindex import LlamaIndex, init_llama
from app.routes.upload import upload_router
from app.routes.query import query_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    embbed_model.init()
    await init_db()
    await init_qdrant()
    await init_groq()
    await init_supabase()
    await init_llama()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api/upload")
app.include_router(query_router, prefix="/api/query")
