import base64
import struct
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pyrogram import raw, utils
from pyrogram.storage import Storage
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    delete,
    select,
    text,
)

from delta.core.database.database_provider import Base


class SessionModel(Base):
    __tablename__ = "sessions"
    session = Column(String, primary_key=True)
    dc_id = Column(Integer, nullable=True)
    api_id = Column(Integer, nullable=True)
    test_mode = Column(Boolean, nullable=True)
    auth_key = Column(LargeBinary, nullable=True)
    date = Column(Integer, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    is_bot = Column(Boolean, nullable=True)


class PeerModel(Base):
    __tablename__ = "peers"
    id = Column(BigInteger, primary_key=True)
    access_hash = Column(BigInteger, nullable=True)
    type = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    last_update_on = Column(
        Integer, nullable=False, server_default=text("EXTRACT(EPOCH FROM now())::int")
    )


class UsernameModel(Base):
    __tablename__ = "usernames"
    id = Column(BigInteger, ForeignKey("peers.id"), primary_key=True)
    username = Column(String, primary_key=True)


class UpdateStateModel(Base):
    __tablename__ = "update_state"
    id = Column(Integer, primary_key=True)
    pts = Column(Integer, nullable=True)
    qts = Column(Integer, nullable=True)
    date = Column(Integer, nullable=True)
    seq = Column(Integer, nullable=True)


class VersionModel(Base):
    __tablename__ = "version"
    number = Column(Integer, primary_key=True)


class PeerType(Enum):
    USER = "user"
    BOT = "bot"
    GROUP = "group"
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"


def get_input_peer(peer: Dict) -> Any:
    peer_id, access_hash, peer_type = peer["id"], peer["access_hash"], peer["type"]
    if peer_type in {PeerType.USER.value, PeerType.BOT.value}:
        return raw.types.InputPeerUser(user_id=peer_id, access_hash=access_hash)
    if peer_type == PeerType.GROUP.value:
        return raw.types.InputPeerChat(chat_id=-peer_id)
    if peer_type in {PeerType.CHANNEL.value, PeerType.SUPERGROUP.value}:
        return raw.types.InputPeerChannel(
            channel_id=utils.get_channel_id(peer_id), access_hash=access_hash
        )
    raise ValueError(f"Invalid peer type: {peer_type}")


_UNSET = object()


class PostgreSQLStorage(Storage):
    USERNAME_TTL = 8 * 60 * 60

    def __init__(self, name: str, async_session):
        self._session_id = name
        self._session_data: Dict[str, Any] = {}
        self.async_session = async_session

    async def open(self):
        async with self.async_session() as session:
            session_obj = await session.get(SessionModel, self._session_id)
            if session_obj is None:
                session_obj = SessionModel(
                    session=self._session_id,
                    dc_id=None,
                    api_id=None,
                    test_mode=None,
                    auth_key=None,
                    date=0,
                    user_id=None,
                    is_bot=None,
                )
                session.add(session_obj)
                await session.commit()
            self._session_data = {
                "session": session_obj.session,
                "dc_id": session_obj.dc_id,
                "api_id": session_obj.api_id,
                "test_mode": session_obj.test_mode,
                "auth_key": session_obj.auth_key,
                "date": session_obj.date,
                "user_id": session_obj.user_id,
                "is_bot": session_obj.is_bot,
            }

    async def save(self):
        await self.date(int(time.time()))

    async def close(self):
        pass

    async def delete(self):
        async with self.async_session() as session:
            session_obj = await session.get(SessionModel, self._session_id)
            if session_obj:
                await session.delete(session_obj)
            await session.execute(delete(PeerModel))
            await session.commit()

    async def update_peers(self, peers: List[Tuple[int, int, str, List[str], str]]):
        if not peers:
            return
        now = int(time.time())
        async with self.async_session() as session:
            for peer_data in peers:
                peer_id, access_hash, peer_type, usernames, phone_number = peer_data
                db_peer = await session.get(PeerModel, peer_id)
                if db_peer:
                    db_peer.access_hash = access_hash
                    db_peer.type = peer_type
                    db_peer.phone_number = phone_number
                    db_peer.last_update_on = now
                else:
                    db_peer = PeerModel(
                        id=peer_id,
                        access_hash=access_hash,
                        type=peer_type,
                        phone_number=phone_number,
                        last_update_on=now,
                    )
                    session.add(db_peer)
                if usernames:
                    await session.execute(
                        delete(UsernameModel).where(UsernameModel.id == peer_id)
                    )
                    for uname in usernames:
                        session.add(UsernameModel(id=peer_id, username=uname))
            await session.commit()

    async def update_state(self, state: Optional[Tuple[int, int, int, int]] = None):
        if state is None:
            async with self.async_session() as session:
                state_obj = await session.get(UpdateStateModel, 1)
                if state_obj is None:
                    return None
                return (state_obj.pts, state_obj.qts, state_obj.date, state_obj.seq)
        pts, qts, date_val, seq = state
        async with self.async_session() as session:
            state_obj = await session.get(UpdateStateModel, 1)
            if state_obj is None:
                state_obj = UpdateStateModel(
                    id=1, pts=pts, qts=qts, date=date_val, seq=seq
                )
                session.add(state_obj)
            else:
                state_obj.pts = pts
                state_obj.qts = qts
                state_obj.date = date_val
                state_obj.seq = seq
            await session.commit()
        return state

    async def get_peer_by_id(self, peer_id: int):
        async with self.async_session() as session:
            peer_obj = await session.get(PeerModel, peer_id)
            if peer_obj is None:
                raise KeyError(f"ID not found: {peer_id}")
            return get_input_peer(
                {
                    "id": peer_obj.id,
                    "access_hash": peer_obj.access_hash,
                    "type": peer_obj.type,
                }
            )

    async def get_peer_by_username(self, username: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(PeerModel)
                .join(UsernameModel, PeerModel.id == UsernameModel.id)
                .where(UsernameModel.username == username)
                .order_by(PeerModel.last_update_on.desc())
            )
            row = result.first()
            if row is None:
                raise KeyError(f"Username not found: {username}")
            peer_obj = row[0]
            if int(time.time() - peer_obj.last_update_on) > self.USERNAME_TTL:
                raise KeyError(f"Username expired: {username}")
            return get_input_peer(
                {
                    "id": peer_obj.id,
                    "access_hash": peer_obj.access_hash,
                    "type": peer_obj.type,
                }
            )

    async def get_peer_by_phone_number(self, phone_number: str):
        async with self.async_session() as session:
            result = await session.execute(
                select(PeerModel).where(PeerModel.phone_number == phone_number)
            )
            peer_obj = result.scalars().first()
            if peer_obj is None:
                raise KeyError(f"Phone number not found: {phone_number}")
            return get_input_peer(
                {
                    "id": peer_obj.id,
                    "access_hash": peer_obj.access_hash,
                    "type": peer_obj.type,
                }
            )

    async def _accessor(self, column: str, value: Any = _UNSET):
        async with self.async_session() as session:
            session_obj = await session.get(SessionModel, self._session_id)
            if value is _UNSET:
                return getattr(session_obj, column)
            setattr(session_obj, column, value)
            await session.commit()
            self._session_data[column] = value
            return value

    async def dc_id(self, value: int = _UNSET):
        return await self._accessor("dc_id", value)

    async def api_id(self, value: int = _UNSET):
        return await self._accessor("api_id", value)

    async def test_mode(self, value: bool = _UNSET):
        return await self._accessor("test_mode", value)

    async def auth_key(self, value: bytes = _UNSET):
        return await self._accessor("auth_key", value)

    async def date(self, value: int = _UNSET):
        return await self._accessor("date", value)

    async def user_id(self, value: int = _UNSET):
        return await self._accessor("user_id", value)

    async def is_bot(self, value: bool = _UNSET):
        return await self._accessor("is_bot", value)

    async def export_session_string(self) -> str:
        packed = struct.pack(
            Storage.SESSION_STRING_FORMAT,
            await self.dc_id(),
            await self.api_id(),
            await self.test_mode(),
            await self.auth_key(),
            await self.user_id(),
            await self.is_bot(),
        )
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")
