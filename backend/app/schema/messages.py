from pydantic import BaseModel


### Message Schema


class MessageSchema(BaseModel):
    query: str
