from pyrogram import Client, filters, types

from delta.utils import gemini_chat


@Client.on_message(filters.mentioned | filters.command(["ai", "delta"]))
async def chatai(client: Client, message: types.Message) -> None:
    if message.command:
        text = " ".join(message.command[1:]) if len(message.command) > 1 else ""
    else:
        text = message.text or ""

    target_user = (
        message.reply_to_message.reply_to_message.from_user
        if message.reply_to_message.reply_to_message
        and not message.reply_to_message.from_user.is_self
        else message.from_user
    )

    if not target_user:
        return

    ai = await gemini_chat.get_chat(target_user.id)
    try:
        resp = await ai.send(str(text))
        await message.reply_text(str(resp))
    except Exception as e:
        await message.reply_text(str(e))
