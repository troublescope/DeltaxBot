import os
from typing import List

from pyrogram import Client, filters, types
from pyrogram.types import Message
from spotdl import Song
from spotipy.exceptions import SpotifyException

from app import config
from app.database import add_music, get_music_by_url
from app.helpers.spotify import spotify
from app.utils import logger


async def download_and_prepare_song(song: Song) -> tuple[Song, str]:
    try:
        song, path = await spotify.download(song)
        if not path:
            raise Exception(f"Download failed for {song.display_name}")
        return song, str(path)
    except Exception as error:
        raise error


@Client.on_message(filters.command("spotdl"))
async def spotdl_cmd(client: Client, message: Message) -> None:
    # Get Spotify URL from message entities.
    spotify_url = None
    if message.entities:
        for entity in message.entities:
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

    # Use the provided query or URL.
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

    prev_message_id = message.id  # For reply chaining.
    for song in songs:
        # Check if the song exists in the database.
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
                        reply_parameters=types.ReplyParameters(
                            message_id=prev_message_id
                        ),
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
            # Send the song to the log channel.
            log_msg = await client.send_audio(
                chat_id=config.channel_log, audio=path, caption=song.display_name
            )
            await add_music(message_id=log_msg.id, url=song.url)
        except Exception as e:
            logger.error(f"Error sending {song.display_name} to log channel: {e}")
            continue
        finally:
            if os.path.exists(path):
                os.remove(path)

        try:
            # Forward the song to the user.
            copied = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=config.channel_log,
                message_id=log_msg.id,
                reply_parameters=types.ReplyParameters(message_id=prev_message_id),
            )
            prev_message_id = copied.id
        except Exception as e:
            logger.error(f"Error copying {song.display_name} to user: {e}")

    await downloading_message.delete()
