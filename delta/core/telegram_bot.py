from pyrogram import Client

from delta import config
from delta.utils import logger

from .database.database_provider import async_session
from .database.storage import PostgreSQLStorage


class DeltaBot:
    def __init__(self):
        self.name = "DeltaBot"
        self.client = None
        self.storage = None
        self.pool = None

    async def init_storage(self):
        # self.pool = await asyncpg.create_pool(dsn=config.database_uri)
        self.storage = PostgreSQLStorage(self.name.lower(), async_session)

    async def start(self) -> Client:
        await self.init_storage()
        self.client = Client(
            self.name.lower(),
            api_id=config.api_id,
            api_hash=config.api_hash,
            bot_token=config.bot_token,
            plugins={"root": "delta.plugins"},
            storage_engine=self.storage,
            workdir="delta",
        )
        await self.client.start()
        logger.info("Bot client started.")
        return self.client

    async def run(self):
        await self.start()
        logger.info("Bot is running.")


deltabot = DeltaBot()
