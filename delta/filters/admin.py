from typing import Union

from pyrogram import Client, filters, types

from delta import config


def flt_owner_only(
    flt: filters.Filter,
    client: Client,
    message: Union[types.Message, types.CallbackQuery],
) -> bool:
    """
    Filter to allow only the owner(s) specified in config.owner_id.

    Args:
        flt: The filter instance (unused in this filter).
        client: The Pyrogram Client instance.
        message: The incoming message or callback query.

    Returns:
        bool: True if the message is from an owner, False otherwise.
    """
    user: types.User = message.from_user
    if not user:
        return False

    # Assumes config.owner_id is a list, tuple, or set of owner IDs
    return user.id in config.owner_id


owner_only = filters.create(flt_owner_only, "OWNER_ONLY")
