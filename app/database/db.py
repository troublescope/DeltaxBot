import logging

import dns.resolver
import motor.motor_asyncio
from beanie import init_beanie

from app import config

from .base import Chat, Music, Stats


class Database:
    def __init__(self, log: logging.Logger, name: str = "DELTAVIP"):
        self.name = name.upper()
        self.log = log
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = ["8.8.8.8"]

    async def start(self):
        self.log.info("Initializing database connection...")
        client = motor.motor_asyncio.AsyncIOMotorClient(config.database_uri)
        await init_beanie(
            database=client[self.name], document_models=[Chat, Stats, Music]
        )
