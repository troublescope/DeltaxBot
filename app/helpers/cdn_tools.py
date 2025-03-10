import aiohttp
from aiopath import AsyncPath
from pyrogram import Client
from pyrogram.types import Message


async def catbox_post(msg: Message | str) -> str:
    path = None
    if isinstance(msg, str):
        path = await Client.download_media(msg)
    elif hasattr(msg, "media") and msg.media:
        media = getattr(msg, msg.media.value)
        if hasattr(media, "file_id") and media.file_id:
            path = await Client.download_media(media.file_id)

    if not path:
        raise ValueError("No valid media found to download.")

    file_path = AsyncPath(path)
    file_bytes = await file_path.read_bytes()

    async with aiohttp.ClientSession() as client:
        form = aiohttp.FormData()
        form.add_field("reqtype", "fileupload")
        form.add_field(
            "fileToUpload",
            file_bytes,
            filename=file_path.name,
            content_type="application/octet-stream",
        )

        await file_path.unlink()

        async with client.post("https://catbox.moe/user/api.php", data=form) as resp:
            resp.raise_for_status()
            url = await resp.text()
            return url.strip()
