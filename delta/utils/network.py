import aiohttp
from pyrogram.types import Message

from delta import deltabot


async def catbox_post(msg: Message | str) -> str:
    file = None

    if isinstance(msg, str):
        file = await deltabot.client.download_media(message=msg, in_memory=True)
    elif hasattr(msg, "media") and msg.media:
        file = await deltabot.client.download_media(message=msg, in_memory=True)

    if not file:
        raise ValueError("No valid media found to download.")

    # Ensure the file pointer is at the beginning
    file.seek(0)

    # Extract filename from the file object
    filename = getattr(file, "name", "upload.dat")

    async with aiohttp.ClientSession() as client:
        form = aiohttp.FormData()
        form.add_field("reqtype", "fileupload")
        form.add_field(
            "fileToUpload",
            file,
            filename=filename,
            content_type="application/octet-stream",
        )

        async with client.post("https://catbox.moe/user/api.php", data=form) as resp:
            resp.raise_for_status()
            url = await resp.text()
            return url.strip()
