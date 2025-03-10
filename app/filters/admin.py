from typing import Union

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, User

from app import config


def owner_filter(
    _: filters.Filter, client: Client, event: Union[Message, CallbackQuery]
) -> bool:
    """
    Allow only messages or callback queries from owners.

    Args:
        _ (filters.Filter): The filter instance (unused).
        client (Client): The Pyrogram client instance.
        event (Union[Message, CallbackQuery]): The incoming message or callback query.

    Returns:
        bool: True if the user is an owner, False otherwise.
    """
    user: Union[User, None] = event.from_user
    return bool(user and user.id in config.owner_id)


def devs_filter(
    _: filters.Filter, client: Client, event: Union[Message, CallbackQuery]
) -> bool:
    """
    Allow only messages or callback queries from sudo users.

    Args:
        _ (filters.Filter): The filter instance (unused).
        client (Client): The Pyrogram client instance.
        event (Union[Message, CallbackQuery]): The incoming event.

    Returns:
        bool: True if the user is a sudo user, False otherwise.
    """
    user: Union[User, None] = event.from_user
    return bool(user and user.id in config.sudo_users)


owner_only = filters.create(owner_filter, "OWNER_ONLY")
devs_only = filters.create(devs_filter, "DEVS_ONLY")
