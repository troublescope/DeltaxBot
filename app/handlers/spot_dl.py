import asyncio

from pyrogram import Client, filters
from pyrogram.types import InputMediaAudio, Message
from spotdl import Song
from spotipy.exceptions import SpotifyException

from app.helpers.spotify import spotify


async def download_and_prepare_song(song: Song) -> tuple[Song, str]:
    """
    Download the song and return a tuple with the Song and the file path.
    """
    try:
        song, path = await spotify.download(song)
        if not path:
            raise Exception(f"Download failed for {song.display_name}")
        return (song, str(path))
    except Exception as error:
        raise error


@Client.on_message(filters.command("spotdl"))
async def spotdl_cmd(client: Client, message: Message) -> None:
    if not message.text:
        return

    parts = message.text.split(" ", 1)
    song_query = parts[1] if len(parts) > 1 else ""

    if not song_query:
        await message.reply_text("Please provide a Spotify link or search query.")
        return

    # Validate that the query looks like a Spotify link

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

    # Download all songs concurrently
    results = await asyncio.gather(
        *[download_and_prepare_song(song) for song in songs], return_exceptions=True
    )

    # Prepare media group (list of InputMediaAudio)
    media_group = []
    for result in results:
        if isinstance(result, Exception):
            # Optionally log the error
            continue
        song, path = result
        media_group.append(InputMediaAudio(media=path, caption=song.display_name))

    if media_group:
        # Send as media group (Telegram allows up to 10 items per media group)
        await client.send_media_group(chat_id=message.chat.id, media=media_group)
    else:
        await message.reply_text("No songs were downloaded successfully.")

    await downloading_message.delete()
