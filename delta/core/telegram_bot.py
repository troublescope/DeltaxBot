import logging
from datetime import datetime

from pyrogram import Client

from delta import config
from delta.core.database.system_db import clear_system, get_system

from ..utils import format_duration
from .database.database_provider import async_session
from .database.storage import PostgreSQLStorage

logger = logging.getLogger("DeltaX")


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
            duration_seconds = int(
                (datetime.now() - system.last_restart).total_seconds()
            )
            duration_text = format_duration(duration_seconds)

            text = (
                f"**System Restart Completed!**\n"
                f"Restart Duration: `{duration_text}`"
            )

            msg = await self.client.edit_message_text(
                chat_id=system.chat_id, message_id=system.restart_id, text=text
            )
            await clear_system(self.client.me.id)

        return self.client

    async def run(self):
        await self.start()


deltabot = DeltaBot()
