import asyncio
import json
import logging
from typing import Optional

import aiohttp
from pyrogram import Client
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup

from app import config, promo_sessions
from app.database import get_chat
from app.helpers import ButtonMaker
from app.utils import expand_id

logger = logging.getLogger(__name__)


class SaweriaSocks:
    def __init__(self, bot: Client, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.stream_key = config.saweria_stream_key
        self.bot = bot
        self.loop = loop or asyncio.get_event_loop()
        self._is_running = False  # Flag internal untuk melacak status koneksi

    @property
    def is_running(self) -> bool:
        """Return True jika stream handler sedang terkoneksi."""
        return self._is_running

    def log_payload(self, payload: dict):
        """Tulis payload donasi mentah ke file log."""
        with open("payload_logs.txt", "a") as log_file:
            log_file.write(json.dumps(payload) + "\n")

    async def process_payment(self, payload: dict) -> dict:
        """
        Proses payload donasi yang masuk.
        Format pesan: "<user_id> | <chat_id> | <msg_id> rest of message"
        """
        try:
            text = payload.get("message", "")
            parts = text.split("|", 2)
            if len(parts) != 3:
                raise ValueError("Invalid message format. Expected 3 parts.")

            user_id_str = parts[0].strip()
            chat_id_str = parts[1].strip()
            msg_id_str = parts[2].split()[0].strip()

            if not (user_id_str.isdigit() and msg_id_str.isdigit()):
                raise ValueError(
                    "Invalid format: user_id dan msg_id harus berupa angka"
                )

            user_id = int(user_id_str)
            msg_id = int(msg_id_str)

            # Hapus pesan asli
            await self.bot.delete_messages(chat_id=user_id, message_ids=msg_id)

            # Minta bukti transaksi dengan mengirim pesan prompt
            prompt = await self.bot.send_message(
                user_id, "Silahkan kirim bukti transaksi (foto)"
            )

            proof = None
            while True:
                # Menunggu user mengirim foto (bukti transaksi)
                listen = await self.bot.listen(chat_id=user_id, user_id=user_id)
                await listen.delete()
                if hasattr(listen, "photo") and listen.photo:
                    proof = listen
                    break
                else:
                    await self.bot.send_message(
                        user_id,
                        "Bukan foto. Silahkan kirim ulang bukti transaksi (foto)",
                    )

            await prompt.delete()

            # Proses berdasarkan tipe chat_id_str (VIP atau Promo)
            if chat_id_str.isdigit() or chat_id_str.lstrip("-").isdigit():
                # Direct chat (VIP)
                chat_id = int(chat_id_str)
                try:
                    invite_obj = await self.bot.create_chat_invite_link(
                        chat_id=chat_id, member_limit=1
                    )
                except FloodWait as fw:
                    logger.warning(
                        f"FloodWait: Menunggu {fw.value} detik sebelum membuat invite link lagi."
                    )
                    await asyncio.sleep(fw.value)
                    invite_obj = await self.bot.create_chat_invite_link(
                        chat_id=chat_id, member_limit=1
                    )
                chat_obj = await get_chat(chat_id, "vip")
                chat_name = chat_obj.name if chat_obj and chat_obj.name else "Chat VIP"
                response_text = (
                    f"Silahkan klik link berikut untuk {chat_name}:\n"
                    f"{invite_obj.invite_link}"
                )
                await self.bot.send_message(user_id, response_text)
            else:
                # Promo session (gunakan kategori "promo")
                session_id = expand_id(chat_id_str)
                if session_id not in promo_sessions:
                    raise ValueError("Session tidak ditemukan!")
                state = promo_sessions[session_id]
                if not state:
                    raise ValueError("Promo session kosong!")

                btn_maker = ButtonMaker()
                for idx, target_chat in enumerate(state, start=1):
                    try:
                        invite_obj = await self.bot.create_chat_invite_link(
                            chat_id=target_chat, member_limit=1
                        )
                    except FloodWait as fw:
                        logger.warning(
                            f"FloodWait: Menunggu {fw.value} detik sebelum membuat invite link lagi."
                        )
                        await asyncio.sleep(fw.value)
                        invite_obj = await self.bot.create_chat_invite_link(
                            chat_id=target_chat, member_limit=1
                        )

                    # Cek database untuk mendapatkan nama chat
                    chat_obj = await get_chat(target_chat, "promo")
                    button_text = (
                        chat_obj.name if chat_obj and chat_obj.name else f"Chat {idx}"
                    )
                    btn_maker.add_button(button_text, url=invite_obj.invite_link)
                    btn_maker.add_row()  # Memisahkan tiap tombol di baris baru

                try:
                    markup: InlineKeyboardMarkup = btn_maker.build()
                    await self.bot.send_message(
                        user_id,
                        "Silahkan klik tombol di bawah untuk bergabung ke chat:",
                        reply_markup=markup,
                    )
                except ValueError as build_err:
                    logger.error("Tidak ada tombol yang tersedia: %s", build_err)
                    await self.bot.send_message(
                        user_id,
                        "Maaf, tidak ada chat yang tersedia untuk bergabung saat ini.",
                    )

            # Copy bukti transaksi ke channel database
            if proof:
                await proof.copy(config.channel_db)

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def send_ping(self, ws):
        """Kirim pesan ping secara periodik untuk menjaga koneksi tetap hidup."""
        while True:
            await asyncio.sleep(30)  # Interval ping, sesuaikan sesuai kebutuhan
            try:
                await ws.send_json({"type": "ping"})
                logger.info("Sent ping")
            except Exception as e:
                logger.error("Error sending ping: %s", e)
                break

    async def listen_stream(self):
        """
        Connect ke WebSocket stream Saweria menggunakan stream key.
        Fungsi ini mendengarkan event donasi dan mengabaikan pesan pong.
        """
        ws_url = f"wss://events.saweria.co/stream?streamKey={self.stream_key}"
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                self._is_running = True
                logger.info("Connected with stream key!")

                # Mulai task untuk mengirim ping
                ping_task = asyncio.create_task(self.send_ping(ws))

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            payload = json.loads(msg.data)
                            # Abaikan pesan "pong"
                            if payload.get("type") == "pong":
                                continue
                            # Jika pesan "donation", proses
                            if payload.get("type") == "donation":
                                donations = payload.get("data", [])
                                for donation in donations:
                                    self.log_payload(donation)
                                    result = await self.process_payment(donation)
                                    logger.info(f"Processed donation: {result}")
                        except Exception as e:
                            logger.error("Error processing websocket message: %s", e)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error("WebSocket error: %s", msg.data)
                        break

                # Koneksi putus, batalkan task ping
                ping_task.cancel()
                self._is_running = False

    async def start(self):
        """
        Mulai stream listener. Jika terjadi error koneksi,
        akan mencoba reconnect setelah delay tertentu.
        """
        while True:
            try:
                await self.listen_stream()
            except aiohttp.ClientResponseError as e:
                # Tangkap error HTTP (termasuk 429)
                self._is_running = False
                if e.status == 429:
                    logger.error(
                        "Rate-limited by Saweria (HTTP 429). Reconnecting in 60 seconds."
                    )
                    await asyncio.sleep(60)  # Tunggu lebih lama untuk menghindari ban
                else:
                    logger.error(
                        f"ClientResponseError {e.status}: {e.message}. Reconnecting in 10 seconds."
                    )
                    await asyncio.sleep(10)
            except Exception as e:
                # Error lain
                self._is_running = False
                logger.error(
                    "Error in websocket connection: %s. Reconnecting in 10 seconds.", e
                )
                await asyncio.sleep(10)
