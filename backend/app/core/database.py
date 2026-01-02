from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models import Base, Document, Conversation, Message

from sqlalchemy import text as sql_text


engine = create_async_engine(
    settings.DB_URL,
    # echo=True,
    future=True,
    connect_args={"server_settings": {"search_path": "public"}},
)

AsyncSessionLocal: sessionmaker[AsyncSession] = sessionmaker(  # type: ignore
    engine,  # type: ignore
    expire_on_commit=False,
    class_=AsyncSession,
)  # type: ignore


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
