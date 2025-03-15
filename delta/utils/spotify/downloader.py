import asyncio
import json
from asyncio import Semaphore
from datetime import datetime

from aiopath import AsyncPath
from asyncer import asyncify
from spotdl import DownloaderOptions, Song
from spotdl.download.downloader import Downloader as BaseDownloader
from spotdl.utils.config import DOWNLOADER_OPTIONS
from spotdl.utils.m3u import gen_m3u_files
from spotdl.utils.search import songs_from_albums

from delta import config, logger


class Downloader(BaseDownloader):
    def __init__(self, settings: DownloaderOptions | None = None):
        bundle_settings: DownloaderOptions = DOWNLOADER_OPTIONS.copy()

        if settings:
            bundle_settings.update(settings)

        bundle_settings["simple_tui"] = True
        bundle_settings["output"] = str(
            AsyncPath(config.download_path).joinpath("spotdl")
        )
        bundle_settings["cookie_file"] = "data/cookies.txt"
        bundle_settings["lyrics_providers"] = ["genius", "azlyrics", "musixmatch"]

        bundle_settings["genius_token"] = config.genius_token
        bundle_settings["bitrate"] = "320K"

        super().__init__(bundle_settings)

        self.semaphore = Semaphore(10)

    async def download_song(self, song: Song) -> tuple[Song, AsyncPath | None]:
        """
        Download a single song.

        ### Arguments
        - song: The song to download.

        ### Returns
        - tuple with the song and the path to the downloaded file if successful.
        """

        self.progress_handler.set_song_count(1)

        return (await self.download_multiple_songs([song]))[0]

    async def download_multiple_songs(
        self, songs: list[Song]
    ) -> list[tuple[Song, AsyncPath | None]]:
        """
        Download multiple songs to the temp directory.

        ### Arguments
        - songs: The songs to download.

        ### Returns
        - list of tuples with the song and the path to the downloaded file if successful.
        """

        if self.settings["fetch_albums"]:
            raw_albums: list[str] = [
                song.album_id for song in songs if song.album_id is not None
            ]
            albums: set[str] = set(raw_albums)

            logger.info(
                "Fetching %d album%s", len(albums), "s" if len(albums) > 1 else ""
            )

            songs.extend(songs_from_albums(list(albums)))
            songs = list({song.url: song for song in songs}.values())

        logger.debug("Downloading %d songs", len(songs))

        if self.settings["archive"]:
            songs = [song for song in songs if song.url not in self.url_archive]
            logger.debug("Filtered %d songs with archive", len(songs))

        self.progress_handler.set_song_count(len(songs))

        results: list[tuple[Song, AsyncPath | None]] = await asyncio.gather(
            *[self.search_and_download(song) for song in songs]
        )

        if self.settings["print_errors"]:
            for error in self.errors:
                logger.error(error)

        if self.settings["save_errors"]:
            # Using aiopath for async file operations
            error_path = AsyncPath(self.settings["save_errors"])
            async with await error_path.open("a") as error_file:
                if len(self.errors) > 0:
                    await error_file.write(
                        f'{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}\n'
                    )

                for error in self.errors:
                    await error_file.write(f"{error}\n")

            logger.info("Saved errors to %s", self.settings["save_errors"])

        if self.settings["archive"]:
            for result in results:
                if result[1] or self.settings["add_unavailable"]:
                    self.url_archive.add(result[0].url)

            await self.url_archive.async_save(self.settings["archive"])
            logger.info(
                "Saved archive with %d urls to %s",
                len(self.url_archive),
                self.settings["archive"],
            )

        if self.settings["m3u"]:
            song_list = [
                song
                for song, path in results
                if path or self.settings["add_unavailable"]
            ]

            # Note: If gen_m3u_files doesn't support AsyncPath, you might need to modify it
            # or convert AsyncPath to str before passing
            [(song, str(path) if path else None) for song, path in results]
            await asyncify(gen_m3u_files)(
                song_list,
                self.settings["m3u"],
                self.settings["output"],
                self.settings["format"],
                self.settings["restrict"],
                False,
                self.settings["detect_formats"],
            )

        if self.settings["save_file"]:
            # Using aiopath for async file operations
            save_path = AsyncPath(self.settings["save_file"])
            async with await save_path.open("w") as save_file:
                await save_file.write(
                    json.dumps(
                        [song.json for song, path in results],
                        indent=4,
                        ensure_ascii=False,
                    )
                )

            logger.info("Saved results to %s", self.settings["save_file"])

        return results

    async def search_and_download(self, song: Song) -> tuple[Song, AsyncPath | None]:
        """
        Search for the song and download it.

        ### Arguments
        - song: The song to download.

        ### Returns
        - tuple with the song and the path to the downloaded file if successful.
        """

        async with self.semaphore:
            result = await asyncify(super().search_and_download)(song)
            # Convert Path to AsyncPath if a path was returned
            if result[1]:
                return (result[0], AsyncPath(result[1]))
            return (result[0], None)
