from pyrogram import Client, filters, types


@Client.on_message(filters.command("start"))
async def start_cmd(client: Client, message: types.Message):
    await message.reply("Working!")
