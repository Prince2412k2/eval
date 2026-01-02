from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.supabase import get_supabase
from app.core.database import get_db
from app.services.chat import ChatService
from app.schema.chat_schema import ConversationCreate
from supabase import AsyncClient


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token"
)  # This tokenUrl is a placeholder, as we're not issuing tokens from here


class TokenData(BaseModel):
    user_id: Optional[str] = None


async def get_current_user(
    token: str = Depends(oauth2_scheme), supabase: AsyncClient = Depends(get_supabase)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Verify the token with Supabase
        user_response = await supabase.auth.get_user(token)
        user = user_response.user

        if user is None:
            raise credentials_exception

        # Supabase user ID is a string (UUID format)
        user_id = user.id
        if user_id is None:
            raise credentials_exception

        return TokenData(user_id=user_id)
    except Exception as e:
        # Catch any exceptions during Supabase verification (e.g., invalid token)
        print(f"Supabase token verification failed: {e}")
        raise credentials_exception


async def get_or_create_welcome_chat(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    user_uuid = UUID(current_user.user_id)
    conversations = await ChatService.get_all_conversations_for_user(user_uuid, db)

    if not conversations:
        # Create a default "Welcome" chat
        welcome_chat_data = ConversationCreate(user_id=user_uuid, title="Welcome")
        welcome_chat = await ChatService.create_conversation(welcome_chat_data, db)
        return welcome_chat.id

    # Return the ID of the first conversation found (could be the welcome chat or an existing one)
    return conversations[0].id

