from pyrogram import Client, filters, types


@Client.on_message(filters.commands("start"))
async def start_cmd(client: Client, message: types.Message) -> str:
    await message.reply("works")
