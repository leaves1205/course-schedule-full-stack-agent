from pydantic import BaseModel, Field
from typing import Literal


class ChatMessage(BaseModel):
    """history of chat messages: user message and assistant response"""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """request for sending a chat message"""

    question: str = Field(min_length=1, description="The user's question")
    history: list[ChatMessage] = Field(default_factory=list)
