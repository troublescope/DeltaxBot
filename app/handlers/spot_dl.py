import asyncio

from pyrogram import Client, filters
from pyrogram.types import InputMediaAudio, Message
from spotdl import Song
from spotipy.exceptions import SpotifyException

from app.helpers.spotify import spotify


async def download_and_prepare_song(song: Song) -> tuple[Song, str]:
    try:
        song, path = await spotify.download(song)
        if not path:
            raise Exception(f"Download failed for {song.display_name}")
        return (song, str(path))
    except Exception as error:
        raise error


def split_into_chunks(lst: list, chunk_size: int = 10):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


@Client.on_message(filters.command("spotdl"))
async def spotdl_cmd(client: Client, message: Message) -> None:
    if not message.text:
        return
    parts = message.text.split(" ", 1)
    song_query = parts[1] if len(parts) > 1 else ""
    if not song_query:
        await message.reply_text("Please provide a Spotify link or search query.")
        return
    downloading_message = await message.reply_text(
        "Downloading music from the link...\nThis process may take a few minutes."
    )
    try:
        songs: list[Song] = await spotify.search([song_query])
    except SpotifyException:
        await downloading_message.edit_text(
            "Could not find or download music from the link. Please try again later or send a different link."
        )
        return
    except Exception:
        await downloading_message.edit_text(
            "An error occurred while processing your request. Please check the link and try again."
        )
        return
    results = await asyncio.gather(
        *[download_and_prepare_song(song) for song in songs], return_exceptions=True
    )
    media_group = []
    for result in results:
        if isinstance(result, Exception):
            continue
        song, path = result
        media_group.append(InputMediaAudio(media=path, caption=song.display_name))
    if media_group:
        for chunk in split_into_chunks(media_group):
            await client.send_media_group(chat_id=message.chat.id, media=chunk)
    else:
        await message.reply_text("No songs were downloaded successfully.")
    await downloading_message.delete()
