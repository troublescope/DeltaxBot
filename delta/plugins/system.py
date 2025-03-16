import os
import sys
from datetime import datetime

import git
from pyrogram import Client, filters, types

from delta.core.database.system_db import update_system


@Client.on_message(filters.command("restart"))
async def restart_handler(client: Client, message: types.Message):
    if len(message.command) > 1 and message.command[1].lower() == "update":
        try:
            repo = git.Repo()
            origin = repo.remotes.origin
            origin.pull()
        except git.exc.InvalidGitRepositoryError:
            repo = git.Repo.init()
            origin = repo.create_remote(
                "origin", "https://github.com/troublescope/DeltaxBot.git"
            )
            origin.fetch()
            repo.create_head("main", origin.refs.master)
            repo.heads.master.set_tracking_branch(origin.refs.master)
            repo.heads.master.checkout(True)

        restart_msg = await message.reply("Repository updated. Restarting bot...")
        await update_system(
            system_id=client.me.id,
            chat_id=message.chat.id,
            new_restart_id=restart_msg.id,
            new_last_restart=datetime.utcnow(),
        )
    else:
        restart_msg = await message.reply("Restarting bot...")
        await update_system(
            system_id=client.me.id,
            chat_id=message.chat.id,
            new_restart_id=restart_msg.id,
            new_last_restart=datetime.utcnow(),
        )

    os.execv(sys.executable, [sys.executable] + sys.argv)
