import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_id: int
    api_hash: str
    bot_token: str
    channel_log: Optional[int] = None
    download_path: str = "downloads"
    database_uri: str
    owner_id: List[int]
    port: int = 80
    webhook_server: bool = True

    # Spotfify thing
    spotify_id: Optional[str] = ""
    spotify_secret: Optional[str] = ""

    @field_validator("owner_id", mode="before")
    def parse_owner_id(cls, v):
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if v.isdigit():
                return [int(v)]
            return [int(item.strip()) for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        raise ValueError(
            "owner_id must be an integer, a comma-separated string, or a list of integers"
        )

    model_config = SettingsConfigDict(
        env_file="config.env" if os.path.exists("config.env") else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


config = Settings()
