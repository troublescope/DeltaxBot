from aiopath import AsyncPath
from asyncer import asyncify
from spotdl import DownloaderOptions, Song
from spotdl.utils.search import get_search_results as _get_search_results
from spotdl.utils.search import parse_query
from spotdl.utils.spotify import SpotifyClient

from .downloader import Downloader


class Spotify:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        settings: DownloaderOptions | None = None,
    ):
        # Initialize the Spotify client globally.
        SpotifyClient.init(
            client_id=client_id, client_secret=client_secret, no_cache=True
        )
        self.downloader = Downloader(settings)

    async def search(self, query: list[str]) -> list[Song]:
        """
        Asynchronously searches for songs using the provided query list.
        This method wraps the synchronous parse_query function with asyncify.
        """
        return await asyncify(parse_query)(
            query=query,
            threads=self.downloader.settings["threads"],
            use_ytm_data=self.downloader.settings["ytm_data"],
            playlist_numbering=self.downloader.settings["playlist_numbering"],
            album_type=self.downloader.settings["album_type"],
            playlist_retain_track_cover=self.downloader.settings[
                "playlist_retain_track_cover"
            ],
        )

    async def get_search_results(self, query: str) -> list[Song]:
        """
        Asynchronously retrieves search results using get_search_results.
        This method wraps the synchronous _get_search_results function with asyncify.
        """
        return await asyncify(_get_search_results)(query)

    async def download(self, song: Song) -> tuple[Song, AsyncPath | None]:
        """
        Downloads the specified song asynchronously.
        Returns a tuple of the Song object and the AsyncPath to the downloaded file (or None if not available).
        """
        return await self.downloader.download_song(song)
