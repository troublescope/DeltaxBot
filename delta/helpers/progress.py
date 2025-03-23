import time
from datetime import timedelta
from typing import Literal, Union

from pyrogram.errors import FloodWait
from pyrogram.types import CallbackQuery, Message

from delta.utils import format_duration, human_readable_bytes


def progress_func(
    current: int,
    total: int,
    msg: Union[Message, CallbackQuery],
    start_time: float,
    mode: Literal["upload", "download"],
    file_name: str,
    update_interval: float = 0.5,
    last_update_time: list = [0],
) -> None:
    """
    Callback to display upload/download progress with rate limiting to avoid too frequent updates.

    Args:
        current (int): Bytes processed so far.
        total (int): Total bytes to process.
        start_time (float): Process start time (timestamp).
        mode (Literal["upload", "download"]): Process mode.
        file_name (str): Name of file being processed.
        update_interval (float): Minimum seconds between progress updates.
        last_update_time (list): Mutable list to track last update time between calls.
    """
    # Skip updates that are too frequent (except for 100% completion)
    current_time = time.time()
    if current < total and current_time - last_update_time[0] < update_interval:
        return
    last_update_time[0] = current_time

    # Handle edge cases
    if total <= 0:
        percent = 0
    else:
        percent = min(1.0, current / total)  # Cap at 100%

    elapsed_time = current_time - start_time

    # Calculate speed and ETA
    if elapsed_time > 0 and current > 0:
        speed = current / elapsed_time
        if speed > 0:
            eta_seconds = int((total - current) / speed)
            eta = timedelta(seconds=eta_seconds)
        else:
            eta = timedelta(seconds=0)
    else:
        speed = 0
        eta = timedelta(seconds=0)

    # Create a more visually appealing progress bar
    bar_length = 10
    completed_units = int(round(percent * bar_length))
    progress_bar = "●" * completed_units + "○" * (bar_length - completed_units)

    # Format the status message
    status = "Uploading" if mode == "upload" else "Downloading"
    progress_message = (
        f"`{file_name}`\n"
        f"Status: **{status}**\n"
        f"Progress: [{progress_bar}] {round(percent * 100)}%\n"
        f"{human_readable_bytes(current)} of {human_readable_bytes(total)} @ {human_readable_bytes(speed, suffix='/s')}\n"
        f"ETA: {format_duration(eta)}\n\n"
    )

    try:
        await msg.edit(progress_message)
    except FloodWait as e:
        asyncio.sleep(e.value)
    except Exception as e:
        await msg.edit(str(e))
