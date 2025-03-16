import aiorun

try:
    import uvloop

    uvloop.install()
    uvloop_installed = True
except ImportError:
    uvloop_installed = False

import logging
import os
from datetime import datetime

from colorlog import ColoredFormatter

from delta import deltabot
from delta.core import init_db


def setup_logging():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    log_filename = f"logs/app_{datetime.now().strftime('%Y-%m-%d')}.log"

    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
    )
    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(file_formatter)

    logger = logging.getLogger("DeltaX")
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Adjust third party loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("pyrogram").setLevel(logging.WARNING)

    # Silence SQLAlchemy engine logging completely
    sa_engine_logger = logging.getLogger("sqlalchemy.engine")
    sa_engine_logger.setLevel(logging.ERROR)
    sa_engine_logger.disabled = True

    sa_engine_engine_logger = logging.getLogger("sqlalchemy.engine.Engine")
    sa_engine_engine_logger.setLevel(logging.ERROR)
    sa_engine_engine_logger.disabled = True

    return logger


logger = setup_logging()


async def shutdown(loop):
    logger.info("Graceful shutdown completed")


async def main():
    try:
        await init_db()
        logger.info("Starting bot client")
        await deltabot.start()
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
