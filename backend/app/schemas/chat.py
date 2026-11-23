from pydantic import BaseModel, Field, field_validator
from typing import Literal

# Chat input is untrusted and every message costs paid model calls, so its size is bounded.
MAX_QUESTION_CHARS = 2000
MAX_MESSAGE_CHARS = 8000
MAX_HISTORY_MESSAGES = 20


class ChatMessage(BaseModel):
    """history of chat messages: user message and assistant response"""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    """request for sending a chat message"""

    question: str = Field(
        min_length=1, max_length=MAX_QUESTION_CHARS, description="The user's question"
    )
    history: list[ChatMessage] = Field(default_factory=list)

    @field_validator("history")
    @classmethod
    def keep_recent_history(cls, history: list[ChatMessage]) -> list[ChatMessage]:
        """Keep only the latest turns instead of rejecting long conversations.

        The history comes from the browser, so it is never trusted to be short, and the window
        always starts with a user message.
        """
        recent = history[-MAX_HISTORY_MESSAGES:]
        while recent and recent[0].role == "assistant":
            recent = recent[1:]
        return recent
