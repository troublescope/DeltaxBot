from datetime import datetime
from typing import Literal, Optional

from beanie import Document
from pydantic import root_validator


class Chat(Document):
    """
    Chat model that supports both private and group chats.

    - For a private chat, only user_id is provided.
    - For a group chat, chat_id is provided and chat_type must be either "group" or "supergroup".
    """

    chat_id: Optional[int] = None
    user_id: Optional[int] = None
    chat_type: Optional[Literal["group", "supergroup"]] = None
    created_at: datetime = datetime.utcnow()

    @root_validator
    def validate_chat(cls, values):
        chat_id = values.get("chat_id")
        user_id = values.get("user_id")
        chat_type = values.get("chat_type")

        if chat_id and user_id:
            raise ValueError(
                "Provide either chat_id (for group chats) or user_id (for private chats), not both."
            )
        if not chat_id and not user_id:
            raise ValueError(
                "Either chat_id (for group chats) or user_id (for private chats) must be provided."
            )

        if chat_id:
            if chat_type not in {"group", "supergroup"}:
                raise ValueError(
                    "For group chats, chat_type must be 'group' or 'supergroup'."
                )
        if user_id:
            if chat_type is not None:
                raise ValueError("For private chats, chat_type should not be provided.")
        return values

    class Settings:
        name = "chats"


class Stats(Document):
    """
    Statistics model for storing aggregated counts such as total number of private chats,
    group chats, and messages.
    """

    total_private_chats: int = 0
    total_group_chats: int = 0
    total_messages: int = 0
    updated_at: datetime = datetime.utcnow()

    class Settings:
        name = "stats"
