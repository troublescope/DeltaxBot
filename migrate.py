import asyncio

import dns.resolver
import motor.motor_asyncio
from beanie import init_beanie

from app import config
from app.database import add, set_settings
from app.database.models import AppSettings, Chat

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ["8.8.8.8"]


async def main():
    # Initialize MongoDB connection using Motor
    client = motor.motor_asyncio.AsyncIOMotorClient(config.database_uri)
    db = client["DELTAVIP"]

    # Initialize Beanie with your models
    await init_beanie(database=db, document_models=[Chat, AppSettings])

    # Set default app settings for all categories: promo, start, and vip
    categories = ["promo", "start", "vip"]
    for cat in categories:
        result = await set_settings(
            welcome="<b>Hello! Pilih chat dari daftar di bawah:</b>",
            banner="https://files.catbox.moe/o9xxq4.jpg",
            cat=cat,
        )
        print(result)

    # Optionally, add a chat for testing purposes
    result = await add(chat_id=123456, name="Test Chat", price=10000, cat="vip")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
