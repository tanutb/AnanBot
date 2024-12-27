from pydantic import BaseModel
from typing import Optional


# Chat request model
class ChatRequest(BaseModel):
    text: str
    image_path: Optional[str] = None

