from aiopath import AsyncPath
from pyrogram import Client, filters, types

from delta.utils import gemini_chat


def split_text(text: str, limit: int = 4000) -> list[str]:
    """Splits the given text into chunks not exceeding 'limit' characters."""
    return [text[i : i + limit] for i in range(0, len(text), limit)]


@Client.on_message(filters.mentioned | filters.command(["ai", "delta"]), group=10)
async def chatai(client: Client, message: types.Message) -> None:

    target_user = (
        message.reply_to_message.reply_to_message.from_user
        if message.reply_to_message
        and message.reply_to_message.reply_to_message
        and not message.reply_to_message.from_user.is_self
        else message.from_user
    )
    if not target_user:
        return

    text = (
        " ".join(message.command[1:])
        if message.command and len(message.command) > 1
        else (message.text or message.caption or "")
    )

    ai = await gemini_chat.get_session(target_user.id)
    msg = message.reply_to_message or message
    if getattr(msg, "photo", None):
        photo_path = None
        try:
            photo_path = await msg.download()
            async_photo = AsyncPath(photo_path)
            resp = await ai.vision(photo_path, str(text))
            # Check if response exceeds 4000 characters
            if len(resp) > 4000:
                parts = split_text(resp, 4000)
                first_reply = await msg.reply_text(parts[0])
                for part in parts[1:]:
                    await first_reply.reply_text(part)
            else:
                await msg.reply_text(resp)
        except Exception as e:
            await msg.reply_text(str(e))
        finally:
            if photo_path:
                try:
                    await async_photo.unlink()
                except Exception:
                    pass
    else:
        try:
            resp = await ai.send_message(str(text))
            # Check if response exceeds 4000 characters
            if len(resp) > 4000:
                parts = split_text(resp, 4000)
                first_reply = await message.reply_text(parts[0])
                for part in parts[1:]:
                    await first_reply.reply_text(part)
            else:
                await message.reply_text(resp)
        except Exception as e:
            await message.reply_text(str(e))
