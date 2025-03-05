import os

from dotenv import load_dotenv


def load_var(env_file="config.env"):
    """
    Load environment variables from a specified file or fallback to .env

    Args:
        env_file (str): Primary environment file path to load
    """
    if os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        load_dotenv(".env")


load_var()


class Config:
    """
    Configuration class that loads and validates required environment variables.

    Required Environment Variables:
        - API_ID: Integer
        - API_HASH: String
        - BOT_TOKEN: String
        - OWNER_ID: List of Integers
        - DATABASE_URI: String

    Optional Environment Variables:
        - CHANNEL_DB: Integer (defaults to 0)
        - SAWERIA_EMAIL: String
        - SAWERIA_PASSWORD: String
        - SAWERIA_STREAM_KEY: String
        - PORT: Integer (defaults to 80)
        - WEBHOOK_SERVER: Boolean (defaults to True)

    Raises:
        ValueError: If any required environment variables are missing
        RuntimeError: If there's an error during configuration loading
    """

    try:
        api_id = int(os.environ.get("API_ID", 0))
        api_hash = os.environ.get("API_HASH", "")
        bot_token = os.environ.get("BOT_TOKEN", "")
        owner_id = list(map(int, os.environ.get("OWNER_ID", "").split(",")))
        database_uri = os.environ.get("DATABASE_URI", "")
        channel_db = int(os.environ.get("CHANNEL_DB", 0))
        saweria_email = os.environ.get("SAWERIA_EMAIL", "")
        saweria_password = os.environ.get("SAWERIA_PASSWORD", "")
        saweria_stream_key = os.environ.get("SAWERIA_STREAM_KEY", "")
        channel_log = os.environ.get("CHANNEL_LOG")
        channel_log = int(channel_log) if channel_log is not None else None
        port = int(os.environ.get("PORT", 80))
        webhook_server = os.environ.get("WEBHOOK_SERVER", "false").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )

        if not all([api_id, api_hash, bot_token, owner_id, database_uri]):
            raise ValueError("Required environment variables are missing!")
    except Exception as e:
        raise RuntimeError(f"Configuration error: {e}")


config = Config()
