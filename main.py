import aiorun

try:
    import uvloop

    uvloop.install()
    uvloop_installed = True
except ImportError:
    uvloop_installed = False

from app import bot
from app.database import Database
from app.utils.logger import logger


async def shutdown(loop):
    logger.info("Graceful shutdown completed")


async def main():
    try:

        init_db = Database(logger)
        await init_db.start()
        logger.info("Database connection established")

        logger.info("Starting bot client")

        await bot.start()
        logger.info("Application started successfully")
    except Exception as e:
        logger.critical("Failed to start application: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    if uvloop_installed:
        logger.info("uvloop installed as default event loop")
    else:
        logger.info("uvloop not available, using default asyncio event loop")

    logger.info("Starting application with aiorun")
    aiorun.run(main(), shutdown_callback=shutdown)
