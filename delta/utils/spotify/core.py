import os
from typing import List, Optional, Tuple

import aiohttp
from aiopath import AsyncPath
from asyncer import asyncify
from spotdl import DownloaderOptions, Song
from spotdl.utils.search import get_search_results as _get_search_results
from spotdl.utils.search import parse_query
from spotdl.utils.spotify import SpotifyClient

from .downloader import Downloader


class Spotify:
    """
    Asynchronous wrapper for the spotdl library to search and download Spotify songs.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        settings: Optional[DownloaderOptions] = None,
    ):
        """
        Initialize the Spotify client with credentials and downloader settings.

        Args:
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
            settings: Optional downloader settings
        """
        # Initialize the Spotify client globally
        SpotifyClient.init(
            client_id=client_id, client_secret=client_secret, no_cache=True
        )
        self.downloader = Downloader(settings)

    async def search(self, query: List[str]) -> List[Song]:
        """
        Asynchronously search for songs using the provided query list.

        Args:
            query: List of search queries (URLs or keywords)

        Returns:
            List of Song objects matching the queries
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

    async def get_search_results(self, query: str) -> List[Song]:
        """
        Asynchronously retrieve search results for a single query string.

        Args:
            query: Search query string

        Returns:
            List of Song objects matching the query
        """
        return await asyncify(_get_search_results)(query)

    async def download(self, song: Song) -> Tuple[Song, Optional[AsyncPath]]:
        """
        Download the specified song asynchronously.

        Args:
            song: Song object to download

        Returns:
            Tuple containing the Song object and path to the downloaded file (or None if download failed)
        """
        return await self.downloader.download_song(song)

    async def download_thumbnail(self, song: Song, output_dir: str = "") -> str:
        """
        Download thumbnail from the song's cover URL and save it as a file.

        Args:
            song: Song object containing the cover URL
            output_dir: Optional directory to save thumbnail (defaults to current directory)

        Returns:
            Path to the downloaded thumbnail file

        Raises:
            Exception: If thumbnail download fails
        """
        if not song.cover_url:
            raise ValueError("Song does not have a cover URL")

        # Create safe filename from song name
        safe_name = "".join(c for c in song.name if c.isalnum() or c in " ._-").strip()

        # Create output directory if it doesn't exist
        if output_dir and not await AsyncPath(output_dir).exists():
            await AsyncPath(output_dir).mkdir(parents=True)

        # Create full path for thumbnail
        thumb_path = (
            os.path.join(output_dir, f"{safe_name}.jpeg")
            if output_dir
            else f"{safe_name}.jpeg"
        )
        thumb_file = AsyncPath(thumb_path)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(song.cover_url, timeout=30) as response:
                    response.raise_for_status()
                    data = await response.read()
                    await thumb_file.write_bytes(data)
                    return str(thumb_file)
        except aiohttp.ClientError as e:
            raise Exception(f"Failed to download thumbnail: {str(e)}")
        except asyncio.TimeoutError:
            raise Exception("Thumbnail download timed out")
        except Exception as e:
            raise Exception(f"Error downloading thumbnail: {str(e)}")
