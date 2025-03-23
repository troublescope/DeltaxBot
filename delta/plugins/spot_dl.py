import html
import logging
import os
import uuid
from typing import List, Tuple

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultPhoto,
    InputMediaAudio,
    Message,
    ReplyParameters,
)
from spotdl import Song
from spotipy.exceptions import SpotifyException

from delta import config
from delta.core.database.music_db import add_music, get_music_by_url
from delta.utils import spotify

logger = logging.getLogger("DeltaX")


async def download_and_prepare_song(song: Song) -> Tuple[Song, str]:
    try:
        song, path = await spotify.download(song)
        if not path:
            raise Exception(f"Download failed for {song.display_name}")
        return song, str(path)
    except Exception as error:
        raise error


def build_song_caption(song: Song) -> str:
    display_name = html.escape(getattr(song, "display_name", "Unknown Title"))
    artist = html.escape(getattr(song, "artist", "Unknown Artist"))
    album = html.escape(getattr(song, "album_name", "Unknown Album"))

    # Convert duration from seconds to minutes and seconds
    duration_val = getattr(song, "duration", None)
    if duration_val is None or not str(duration_val).isdigit():
        duration_str = "Unknown Duration"
    else:
        duration_seconds = int(duration_val)
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        duration_str = f"{minutes} min {seconds} sec"

    explicit = getattr(song, "explicit", "No")
    publisher = html.escape(getattr(song, "publisher", "Unknown Publisher"))
    popularity = getattr(song, "popularity", "0")
    year = getattr(song, "year", "0")
    caption = (
        f"<b>{display_name}</b>\n\n"
        f'<pre language="Artist">{artist}</pre>\n'
        f'<pre language="Album">{album}</pre>\n'
        f'<pre language="Year">{year}</pre>\n'
        f'<pre language="Duration">{duration_str}</pre>\n'
        f'<pre language="Explicit">{explicit}</pre>\n'
        f'<pre language="Popularity">{popularity}</pre>\n'
        f'<pre language="Publisher">{publisher}</pre>\n'
    )
    return caption


@Client.on_message(filters.command("spotdl"))
async def spotdl_cmd(client: Client, message: Message) -> None:
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
    # Split the message into the command and the query.
    parts = message.text.split(" ", 1)
    song_query = parts[1] if len(parts) > 1 else spotify_url
    if not song_query:
        await message.reply_text("Please provide a Spotify link or search query.")
        return
    downloading_message = await message.reply_text(
        "Processing your request...\nThis may take a few minutes.", quote=True
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
    prev_message_id = message.id
    for song in songs:
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
        try:
            song_obj, path = await download_and_prepare_song(song)
        except Exception as e:
            logger.error(f"Error downloading {song.display_name}: {e}")
            continue
        try:
            caption = build_song_caption(song)
            log_msg = await client.send_audio(
                chat_id=config.channel_log, audio=path, caption=caption
            )
            await add_music(message_id=log_msg.id, url=song.url)
        except Exception as e:
            logger.error(f"Error sending {song.display_name} to log channel: {e}")
            continue
        finally:
            if os.path.exists(path):
                os.remove(path)
        try:
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


async def download_and_check_song(client: Client, song: Song) -> Tuple[str, str]:
    record = await get_music_by_url(song.url)
    if record and record.message_id:
        try:
            log_msg = await client.get_messages(config.channel_log, record.message_id)
            if log_msg and log_msg.audio:
                caption = build_song_caption(song)
                return log_msg.audio.file_id, caption
        except Exception as e:
            logger.error(f"Error retrieving cached song for {song.url}: {e}")
    song_obj, path = await download_and_prepare_song(song)
    caption = build_song_caption(song)
    thumb = await spotify.download_thumbnail(song)
    try:
        log_msg = await client.send_audio(
            chat_id=config.channel_log,
            audio=path,
            caption=caption,
            title=song.name,
            performer=song.artist,
            duration=int(song.duration),
            thumb=thumb,
        )

        await add_music(message_id=log_msg.id, url=song.url)
    except Exception as e:
        logger.error(f"Error sending {song.display_name} to log channel: {e}")
        raise e
    finally:
        if os.path.exists(path):
            os.remove(path)
            os.remove(thumb)
    return log_msg.audio.file_id, caption


@Client.on_callback_query(filters.regex(r"^spotdl\|[0-9a-fA-F]{8}$"))
async def callback_download_handler(client: Client, callback_query: CallbackQuery):
    song_url = client.message_cache.store.get(callback_query.data)
    await callback_query.edit_message_text("**Download in progress...**")
    try:
        await callback_query.edit_message_text("Downloading ....")
        songs = await spotify.search([song_url])
        for song in songs:
            try:
                audio_file_id, caption = await download_and_check_song(client, song)
            except Exception:
                await callback_query.answer("Error downloading song.", show_alert=True)
                return
    except Exception as e:
        logger.error(f"Error retrieving song for URL {song_url}: {e}")
        await callback_query.answer("Error retrieving song.", show_alert=True)
        return

    try:
        await client.edit_inline_media(
            inline_message_id=callback_query.inline_message_id,
            media=InputMediaAudio(media=audio_file_id, caption=caption),
        )
        await callback_query.answer("Song downloaded successfully!")
    except Exception as e:
        logger.error(f"Error editing inline media for {song.display_name}: {e}")
        await callback_query.answer("Error sending audio.", show_alert=True)


@Client.on_inline_query(filters.regex(r"^spotdl"))
async def inline_query_handler(client: Client, inline_query: InlineQuery):
    not_found_photo = "https://files.catbox.moe/uepygh.jpg"
    parts = inline_query.query.split(" ", 1)
    query = parts[1].strip() if len(parts) > 1 else ""
    if not query:
        return
    try:
        songs = await spotify.get_search_results(query)
    except Exception:
        result = InlineQueryResultPhoto(
            id="not_found",
            photo_url=not_found_photo,
            thumbnail_url=not_found_photo,
            caption="Coba gunakan format (spotdl musik - artist)",
        )
        return await inline_query.answer([result], cache_time=0)
    if not songs:
        result = InlineQueryResultPhoto(
            id="not_found",
            photo_url=not_found_photo,
            thumbnail_url=not_found_photo,
            caption="Not found",
        )
        return await inline_query.answer([result], cache_time=0)
    results = []
    for song in songs:
        song_url = getattr(song, "url", "") or ""
        display_name = getattr(song, "display_name", "Unknown Title") or "Unknown Title"
        artist = getattr(song, "artist", "Unknown Artist") or "Unknown Artist"
        cover_url = getattr(song, "cover_url", "") or ""
        if not song_url or not cover_url:
            continue

        cb_data = "spotdl|" + str(uuid.uuid4()).split("-")[0]
        client.message_cache.store.update({cb_data: song_url})
        result = InlineQueryResultPhoto(
            id=song_url,
            photo_url=cover_url,
            thumbnail_url=cover_url,
            title=display_name,
            description=artist,
            caption=f"{display_name} - {artist}\nPress 'Download' to get the audio.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Download", callback_data=cb_data)]]
            ),
        )
        results.append(result)
    if not results:
        result = InlineQueryResultPhoto(
            id="not_found",
            photo_url=not_found_photo,
            thumbnail_url=not_found_photo,
            caption="Not found",
        )
        results.append(result)
    await inline_query.answer(results, cache_time=0)
