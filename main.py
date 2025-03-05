import aiorun

from app.database import init_db
from app.telegram_bot import start_bot
from app.utils.logger import logger


async def shutdown(loop):
    logger.info("Graceful shutdown completed")


async def main():
    try:
        logger.info("Initializing database connection")
        await init_db()
        logger.info("Database connection established")
        logger.info("Starting bot client")
        await start_bot()
        logger.info("Application started successfully")
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    logger.info("Starting application with aiorun")
    aiorun.run(main(), shutdown_callback=shutdown)
