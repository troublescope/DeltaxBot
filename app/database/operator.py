from datetime import datetime
from typing import Optional

from pyrogram import types

from .base import Chat, Stats


async def create_chat(
    *,
    chat_id: Optional[int] = None,
    user_id: Optional[int] = None,
    chat_type: Optional[str] = None,
) -> Chat:
    """
    Create a new chat record.

    For a private chat, provide only user_id.
    For a group chat, provide chat_id and chat_type (must be "group" or "supergroup").
    """
    chat = Chat(chat_id=chat_id, user_id=user_id, chat_type=chat_type)
    await chat.insert()
    return chat


async def create(chat: types.Chat) -> Chat:
    """
    Create a chat record from a Pyrogram Chat object.

    For a private chat, only the user_id is stored.
    For a group chat, both chat_id and chat_type are stored.
    """
    if chat.type == "private":
        return await create_chat(user_id=chat.id)
    elif chat.type in ("group", "supergroup"):
        return await create_chat(chat_id=chat.id, chat_type=chat.type)
    else:
        raise ValueError(f"Unsupported chat type: {chat.type}")


async def get_chat(identifier: int, is_group: bool = False) -> Optional[Chat]:
    """
    Retrieve a chat record by identifier.

    If is_group is True, the identifier is treated as chat_id;
    otherwise, as user_id.
    """
    if is_group:
        return await Chat.find_one(Chat.chat_id == identifier)
    else:
        return await Chat.find_one(Chat.user_id == identifier)


async def update_chat(
    identifier: int, is_group: bool = False, **kwargs
) -> Optional[Chat]:
    """
    Update fields of a chat record by identifier.
    """
    chat = await get_chat(identifier, is_group)
    if chat:
        for key, value in kwargs.items():
            setattr(chat, key, value)
        await chat.save()
    return chat


async def delete_chat(identifier: int, is_group: bool = False) -> bool:
    """
    Delete a chat record by identifier.

    Returns True if deletion was successful.
    """
    chat = await get_chat(identifier, is_group)
    if chat:
        await chat.delete()
        return True
    return False


async def get_stats() -> Stats:
    """
    Retrieve the stats record. If none exists, create a new one.
    """
    stats = await Stats.find_one({})
    if stats is None:
        stats = Stats()
        await stats.insert()
    return stats


async def increment_private_chats(count: int = 1) -> Stats:
    """
    Increment the total_private_chats counter.
    """
    stats = await get_stats()
    stats.total_private_chats += count
    stats.updated_at = datetime.utcnow()
    await stats.save()
    return stats


async def increment_group_chats(count: int = 1) -> Stats:
    """
    Increment the total_group_chats counter.
    """
    stats = await get_stats()
    stats.total_group_chats += count
    stats.updated_at = datetime.utcnow()
    await stats.save()
    return stats


async def increment_messages(count: int = 1) -> Stats:
    """
    Increment the total_messages counter.
    """
    stats = await get_stats()  # Fixed: proper function call syntax
    stats.total_messages += count
    stats.updated_at = datetime.utcnow()
    await stats.save()
    return stats
