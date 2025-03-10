import os
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration settings.
    """

    api_id: int
    api_hash: str
    bot_token: str
    channel_log: Optional[int] = None
    download_path: str = "downloads"
    database_uri: str
    devs_id: List[int] = [5466401085]  # Default value as a list of integers.
    owner_id: List[int]
    port: int = 80
    webhook_server: bool = True

    # Spotify configuration
    spotify_id: Optional[str] = ""
    spotify_secret: Optional[str] = ""

    @field_validator("owner_id", "devs_id", mode="before")
    def parse_id_list(cls, v: Union[int, str, List[int]]) -> List[int]:
        """
        Validates and parses the owner_id and devs_id fields, ensuring they are lists of integers.

        Args:
            v (Union[int, str, List[int]]): The input value to be validated.

        Returns:
            List[int]: A list of integer IDs.

        Raises:
            ValueError: If the input cannot be converted to a list of integers.
        """
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            v = v.strip()
            if v.isdigit():
                return [int(v)]
            # Convert comma-separated string to list of integers.
            id_list = []
            for item in v.split(","):
                item = item.strip()
                if item.isdigit():
                    id_list.append(int(item))
                else:
                    raise ValueError(f"Invalid integer value in list: '{item}'")
            return id_list
        if isinstance(v, list):
            if all(isinstance(item, int) for item in v):
                return v
            raise ValueError("All items in the list must be integers.")
        raise ValueError(
            "owner_id and devs_id must be an int, a comma-separated string, or a list of integers."
        )

    model_config = SettingsConfigDict(
        env_file="config.env" if os.path.exists("config.env") else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config = Settings()
