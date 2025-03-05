from typing import Optional, Tuple

from pyrogram import types

from . import ButtonMaker


async def parse_info(
    client, user: "types.User"
) -> Tuple[Optional[str], str, "types.InlineKeyboardMarkup", str]:
    bm = ButtonMaker()
    bm.add_button(
        text=f"Open {user.first_name}'s Profile",
        user_id=user.id,
        row=0,
    )
    keyboard = bm.build()
    mention = f"\n<blockquote>{user.mention('#MENTION')}</blockquote>"
    fmt_str = f"<pre language='Started by'>ID  : {user.id}\nName: {user.full_name}\nLang: {user.language_code}</pre>"
    photo = (
        await client.download_media(user.photo.big_file_id)
        if hasattr(user, "photo") and user.photo
        else None
    )
    return photo, fmt_str, keyboard, mention
