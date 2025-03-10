import html
import os
from typing import List, Tuple

from pyrogram import Client, filters
from pyrogram.types import Message, ReplyParameters
from spotdl import Song
from spotipy.exceptions import SpotifyException

from app import config
from app.database import add_music, get_music_by_url
from app.helpers.spotify import spotify
from app.utils import logger


async def download_and_prepare_song(song: Song) -> Tuple[Song, str]:
    try:
        song, path = await spotify.download(song)
        if not path:
            raise Exception(f"Download failed for {song.display_name}")
        return song, str(path)
    except Exception as error:
        raise error


def build_song_caption(song: Song) -> str:
    """
    Build a robust HTML caption for a song.
    Uses html.escape() to ensure that any special characters are safely escaped.
    """
    display_name = html.escape(getattr(song, "display_name", "Unknown Title"))
    artist = html.escape(getattr(song, "artist", "Unknown Artist"))
    album = html.escape(getattr(song, "album_name", "Unknown Album"))
    duration = getattr(song, "duration", "Unknown Duration")
    explicit = getattr(song, "explicit", "No")
    publisher = html.escape(getattr(song, "publisher", "Unknown Publisher"))
    popularity = getattr(song, "popularity", "0")
    year = getattr(song, "year", "0")
    track_number = getattr(song, "track_number", "0")
    track_count = getattr(song, "track_count", "0")

    caption = (
        f"<b>{display_name}</b>\n"
        f'<pre language="Artist">{artist}</pre>\n'
        f'<pre language="Album">{album}</pre>\n'
        f'<pre language="Year">{year}</pre>\n'
        f'<pre language="Duration">{duration} Minute</pre>\n'
        f'<pre language="Explicit">{explicit}</pre>\n'
        f'<pre language="Track Number">{track_number} - {track_count}</pre>\n'
        f'<pre language="Popularity">{popularity}</pre>\n'
        f'<pre language="Publisher">{publisher}</pre>\n'
    )
    return caption


@Client.on_message(filters.command("spotdl"))
async def spotdl_cmd(client: Client, message: Message) -> None:
    # Extract Spotify URL from the message entities if available.
    spotify_url = None
    if message.entities:
        for entity in message.entities:
            # Entity can be a dict or a MessageEntity object.
            etype = entity.get("type") if isinstance(entity, dict) else entity.type
            if etype == "MessageEntityType.URL":
                offset = (
                    entity.get("offset") if isinstance(entity, dict) else entity.offset
                )
                length = (
                    entity.get("length") if isinstance(entity, dict) else entity.length
                )
                url_text = message.text[offset : offset + length]
                if "spotify.com" in url_text:
                    spotify_url = url_text
                    break

    # Use the provided query (if any) or the URL extracted above.
    parts = message.text.split(" ", 1)
    song_query = parts[1] if len(parts) > 1 else spotify_url
    if not song_query:
        await message.reply_text("Please provide a Spotify link or search query.")
        return

    downloading_message = await message.reply_text(
        "Processing your request...\nThis may take a few minutes.",
        quote=True,
    )

    try:
        songs: List[Song] = await spotify.search([song_query])
    except SpotifyException:
        await downloading_message.edit_text(
            "Could not find or download music. Please try a different link."
        )
        return
    except Exception:
        await downloading_message.edit_text(
            "An error occurred. Please check the link and try again."
        )
        return

    prev_message_id = message.id  # Used for reply chaining.
    for song in songs:
        # Check if this song already exists in the database.
        record = await get_music_by_url(song.url)
        if record and record.message_id:
            try:
                log_msg = await client.get_messages(
                    config.channel_log, record.message_id
                )
                if log_msg and log_msg.audio:
                    copied = await client.copy_message(
                        chat_id=message.chat.id,
                        from_chat_id=config.channel_log,
                        message_id=log_msg.id,
                        reply_parameters=ReplyParameters(message_id=prev_message_id),
                    )
                    prev_message_id = copied.id
                    continue
            except Exception as e:
                logger.error(f"Error copying record for {song.display_name}: {e}")

        # Download and process the song.
        try:
            song_obj, path = await download_and_prepare_song(song)
        except Exception as e:
            logger.error(f"Error downloading {song.display_name}: {e}")
            continue

        try:
            # Build a robust caption for the song.
            caption = build_song_caption(song)
            log_msg = await client.send_audio(
                chat_id=config.channel_log,
                audio=path,
                caption=caption,
            )
            await add_music(message_id=log_msg.id, url=song.url)
        except Exception as e:
            logger.error(f"Error sending {song.display_name} to log channel: {e}")
            continue
        finally:
            if os.path.exists(path):
                os.remove(path)

        try:
            # Forward the sent audio message to the user.
            copied = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=config.channel_log,
                message_id=log_msg.id,
                reply_parameters=ReplyParameters(message_id=prev_message_id),
            )
            prev_message_id = copied.id
        except Exception as e:
            logger.error(f"Error copying {song.display_name} to user: {e}")

    await downloading_message.delete()


if __name__ == "__main__":
    # Create and run the client.
    app = Client(
        "my_account",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        # Optionally set a global parse_mode if needed:
        # parse_mode=types.ParseMode.HTML
    )
    app.run()
