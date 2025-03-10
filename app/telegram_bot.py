from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client

from app import config
from app.database.storage import (
    MongoStorage,
    PeerDoc,
    SessionDoc,
    UpdateStateDoc,
    UsernameDoc,
)
from app.utils import logger


class TelegramBot:
    def __init__(self):
        self.name: str = "DeltaBot"
        self.client: Client = None
        self.storage = None  # Initialize storage later

    async def init_storage(self):
        """
        Initialize the Motor client and Beanie storage.
        """
        mongo_client = AsyncIOMotorClient(config.database_uri)
        await init_beanie(
            database=mongo_client[self.name.upper()],
            document_models=[SessionDoc, PeerDoc, UsernameDoc, UpdateStateDoc],
        )
        self.storage = MongoStorage(
            name=self.name.upper(), connection=mongo_client, remove_peers=False
        )

    async def start(self) -> Client:
        """
        Initialize storage and start the Pyrogram client.
        Returns the started client without blocking.
        """
        await self.init_storage()
        self.client = Client(
            self.name.lower(),
            api_id=config.api_id,
            api_hash=config.api_hash,
            bot_token=config.bot_token,
            plugins={"root": "app.handlers"},
            storage_engine=self.storage,
        )
        await self.client.start()
        logger.info("Bot client started.")

        return self.client

    async def run(self):
        await self.start()
        logger.info("Bot is running.")
