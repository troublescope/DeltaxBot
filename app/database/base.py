from datetime import datetime
from typing import Literal, Optional

from beanie import Document


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


class Music(Document):
    message_id: int
    url: str
    created_at: datetime = datetime.utcnow()

    class Settings:
        name = "musics"
