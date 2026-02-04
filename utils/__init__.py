from pydantic import BaseModel
from typing import Optional


# Chat request model
class ChatRequest(BaseModel):
    text: str
    image_path: Optional[str] = None
    user_id: str = "default_user"
    username: Optional[str] = None
    is_mentioned: bool = False
    karma: int = 0
