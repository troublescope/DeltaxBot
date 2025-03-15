from spotdl import Song
from delta import config

from .core import Spotify
spotify = Spotify(
        client_id=config.spotify_id,
        client_secret=config.spotify_secret,
    )

__all__ = ['spotify', 'Song']
