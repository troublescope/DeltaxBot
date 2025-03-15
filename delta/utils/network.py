import aiohttp
from pyrogram import Client
from pyrogram.types import Message


async def catbox_post(msg: Message | str, client: Client) -> str:
    if isinstance(msg, str):
        # Download media using the file_id or URL
        file = await client.download_media(message=msg, in_memory=True)
    elif isinstance(msg, Message):
        # Download media from the Message object
        file = await msg.download(in_memory=True)
    else:
        raise ValueError("Invalid message type provided.")

    if not file:
        raise ValueError("No valid media found to download.")
    file.seek(0)

    filename = getattr(file, "name", "upload.dat")
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        form.add_field(name="reqtype", value="fileupload")
        form.add_field(
            name="fileToUpload",
            value=file,
            filename=filename,
            content_type="application/octet-stream",
        )

        async with session.post(
            "https://catbox.moe/user/api.php", data=form
        ) as response:
            response.raise_for_status()
            url = await response.text()
            return url.strip()
