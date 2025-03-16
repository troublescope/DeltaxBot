from datetime import datetime

from pyrogram import Client

from delta import config
from delta.core.database.system_db import get_system
from delta.logging import logger

from .database.database_provider import async_session
from .database.storage import PostgreSQLStorage


class DeltaBot:
    def __init__(self):
        self.name = "DeltaBot"
        self.client = None
        self.storage = None

    async def init_storage(self):
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
            skip_updates=False,
            workdir="delta",
        )
        await self.client.start()
        logger.info("Bot client started.")
        system = await get_system(self.client.me.id)
        if system:
            duration = datetime.utcnow() - system.last_restart
            text = (
                f"System Check Point!\n"
                f"Restart Duration: {duration}\n"
                f"Last Updated: {system.last_system_update.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            await self.client.edit_message_text(
                chat_id=system.chat_id, message_id=system.restart_id, text=text
            )

        return self.client

    async def run(self):
        await self.start()


deltabot = DeltaBot()
