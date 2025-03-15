import asyncio
import contextlib
import html
import inspect
import io
import os
import shlex
import sys

import aiohttp
import pyrogram
from meval import meval
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from delta.filters import owner_only
from delta.utils import catbox_post

TASKS = {}

BUTTON_ABORT = [[InlineKeyboardButton("Abort", callback_data="btn_abort")]]
BUTTON_RERUN = [[InlineKeyboardButton("Refresh", callback_data="btn_rerun")]]


@Client.on_callback_query(owner_only & filters.regex(r"^btn_"))
async def evaluate_handler_(client: Client, callback_query: CallbackQuery) -> None:
    command = callback_query.data.split("_")[1]

    chat_id = callback_query.message.chat.id
    message = await client.get_messages(
        chat_id, callback_query.message.reply_to_message.id
    )
    reply_message = await client.get_messages(chat_id, callback_query.message.id)

    if command == "rerun":
        _id_ = f"{chat_id} - {message.id}"
        task = asyncio.create_task(async_evaluate_func(client, message, reply_message))
        TASKS[_id_] = task
        try:
            await task
        except asyncio.CancelledError:
            await reply_message.edit_text(
                "<b>Process Cancelled!</b>",
                reply_markup=InlineKeyboardMarkup(BUTTON_RERUN),
            )
        finally:
            if _id_ in TASKS:
                del TASKS[_id_]
    elif command == "abort":
        cancel_task(task_id=f"{chat_id} - {message.id}")


@Client.on_message(owner_only & filters.command(["e", "eval"]))
async def evaluate_handler(client: Client, message: Message) -> None:
    if len(message.command) == 1:
        await message.reply_text(
            "<b>No Code!</b>",
            quote=True,
            reply_markup=InlineKeyboardMarkup(BUTTON_RERUN),
        )
        return

    reply_message = await message.reply_text(
        "...", quote=True, reply_markup=InlineKeyboardMarkup(BUTTON_ABORT)
    )

    _id_ = f"{message.chat.id} - {message.id}"
    task = asyncio.create_task(async_evaluate_func(client, message, reply_message))
    TASKS[_id_] = task
    try:
        await task
    except asyncio.CancelledError:
        await reply_message.edit_text(
            "<b>Process Cancelled!</b>", reply_markup=InlineKeyboardMarkup(BUTTON_RERUN)
        )
    finally:
        if _id_ in TASKS:
            del TASKS[_id_]


@Client.on_message(owner_only & filters.command("sh"))
async def shell_handler(client: Client, message: Message) -> None:
    if len(message.command) == 1:
        await message.reply_text("<b>No Code!</b>", quote=True)
        return

    reply_message = await message.reply_text("...")

    shell_code = message.text.split(maxsplit=1)[1]
    shlex.split(shell_code)

    init_time = client.loop.time()

    sub_process_sh = await asyncio.create_subprocess_shell(
        shell_code, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await sub_process_sh.communicate()
    bash_print_out = (stdout + stderr).decode().strip()

    converted_time = fmt_secs(client.loop.time() - init_time)

    final_output = f"<pre>{bash_print_out}</pre>\n" f"<b>Elapsed:</b> {converted_time}"
    if len(final_output) > 4096:
        paste_url = await paste_rs(str(bash_print_out))
        bash_buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Output", url=paste_url)]]
        )

        caption = f"<b>Elapsed:</b> {converted_time}"
        await reply_message.edit_text(
            caption, reply_markup=bash_buttons, disable_web_page_preview=True
        )
    else:
        await reply_message.edit_text(final_output)


async def async_evaluate_func(
    client: Client, message: Message, reply_message: Message
) -> None:
    await reply_message.edit_text(
        "<b>Executing...</b>", reply_markup=InlineKeyboardMarkup(BUTTON_ABORT)
    )

    if len(message.text.split()) == 1:
        await reply_message.edit_text(
            "<b>No Code!</b>", reply_markup=InlineKeyboardMarkup(BUTTON_RERUN)
        )
        return

    eval_vars = {
        "asyncio": asyncio,
        "os": os,
        "src": inspect.getsource,
        "sys": sys,
        #
        "pyrogram": pyrogram,
        "enums": pyrogram.enums,
        "errors": pyrogram.errors,
        "raw": pyrogram.raw,
        "types": pyrogram.types,
        #
        "c": client,
        "m": message,
        "r": message.reply_to_message,
        "u": (message.reply_to_message or message).from_user,
        #
        "catbox": catbox_post,
    }

    eval_code = message.text.split(maxsplit=1)[1]

    start_time = client.loop.time()

    file = io.StringIO()
    with contextlib.redirect_stdout(file):
        try:
            meval_out = await meval(eval_code, globals(), **eval_vars)
            print_out = file.getvalue().strip() or str(meval_out) or "None"
        except Exception as exception:
            print_out = repr(exception)

    elapsed_time = client.loop.time() - start_time
    converted_time = fmt_secs(elapsed_time)

    final_output = (
        f"<pre>{html.escape(print_out)}</pre>\n" f"<b>Elapsed:</b> {converted_time}"
    )
    eval_buttons = BUTTON_RERUN.copy()
    if len(final_output) > 4096:
        paste_url = await paste_rs(str(print_out))
        eval_buttons.insert(0, [InlineKeyboardButton("Output", url=paste_url)])

        caption = f"<b>Elapsed:</b> {converted_time}"
        await reply_message.edit_text(
            caption,
            reply_markup=InlineKeyboardMarkup(eval_buttons),
            disable_web_page_preview=True,
        )
    else:
        await reply_message.edit_text(
            final_output, reply_markup=InlineKeyboardMarkup(eval_buttons)
        )


async def paste_rs(content: str) -> str:
    async with aiohttp.ClientSession() as client:
        async with client.post("https://paste.rs", data=content) as resp:
            resp.raise_for_status()
            url = await resp.text()
            return url.strip()


def fmt_secs(secs: int | float) -> str:
    if secs == 0:
        return "None"
    elif secs < 1e-3:
        return f"{secs * 1e6:.3f}".rstrip("0").rstrip(".") + "µs"
    elif secs < 1:
        return f"{secs * 1e3:.3f}".rstrip("0").rstrip(".") + "ms"

    return f"{secs:.3f}".rstrip("0").rstrip(".") + "s"


def cancel_task(task_id: str) -> None:
    task = TASKS.get(task_id, None)
    if task and not task.done():
        return task.cancel()
