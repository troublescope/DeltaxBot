import inspect
import time
from typing import Any, List, Optional, Tuple, Union

from bson.codec_options import CodecOptions
from pymongo.client_session import TransactionOptions
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import (
    Nearest,
    Primary,
    PrimaryPreferred,
    Secondary,
    SecondaryPreferred,
)
from pymongo.write_concern import WriteConcern

try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable

from pyrogram.storage.sqlite_storage import get_input_peer
from pyrogram.storage.storage import Storage

from .base_storage import PeerDoc, SessionDoc, UpdateStateDoc, UsernameDoc

ReadPreferences = Union[
    Primary, PrimaryPreferred, Secondary, SecondaryPreferred, Nearest
]


@runtime_checkable
class DummyMongoClient(Protocol):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def get_database(
        self,
        name: Optional[str] = None,
        *,
        codec_options: Optional[CodecOptions] = None,
        read_preference: Optional[ReadPreferences] = None,
        write_concern: Optional[WriteConcern] = None,
        read_concern: Optional[ReadConcern] = None,
    ):
        raise NotImplementedError

    async def start_session(
        self,
        *,
        causal_consistency: Optional[bool] = None,
        default_transaction_options: Optional[TransactionOptions] = None,
        snapshot: bool = False,
    ):
        raise NotImplementedError


class MongoStorage(Storage):
    """
    Beanie-based storage implementation for a Telegram MTProto session.

    Parameters:
        - name (str): The session name used as the database name.
        - connection (AsyncIOMotorClient): An async Motor client.
        - remove_peers (bool): If True, peers data will be removed on logout.
    """

    USERNAME_TTL = 8 * 60 * 60

    def __init__(
        self, name: str, connection: AsyncIOMotorClient, remove_peers: bool = False
    ):
        super().__init__(name=name)
        self.database = connection[name]
        self._remove_peers = remove_peers

    async def open(self):
        """
        Open the session by ensuring a SessionDoc with _id=0 exists.
        """
        session = await SessionDoc.find_one(SessionDoc._id == 0)
        if session:
            return
        session = SessionDoc(
            dc_id=2,
            api_id=None,
            test_mode=None,
            auth_key=b"",
            date=0,
            user_id=0,
            is_bot=0,
        )
        await session.insert()

    async def save(self):
        pass

    async def close(self):
        pass

    async def delete(self):
        """
        Delete the session document; and if configured, delete all peers.
        """
        session = await SessionDoc.find_one(SessionDoc._id == 0)
        if session:
            await session.delete()
        if self._remove_peers:
            await PeerDoc.find_all().delete()

    async def update_peers(self, peers: List[Tuple[int, int, str, str, str]]):
        """
        Update peers using a list of tuples:
        (peer_id, access_hash, type, username, phone_number)
        """
        s = int(time.time())
        for peer in peers:
            peer_id, access_hash, peer_type, username, phone_number = peer
            doc = await PeerDoc.find_one(PeerDoc._id == peer_id)
            if doc:
                doc.access_hash = access_hash
                doc.type = peer_type
                doc.username = username
                doc.phone_number = phone_number
                doc.last_update_on = s
                await doc.save()
            else:
                new_peer = PeerDoc(
                    _id=peer_id,
                    access_hash=access_hash,
                    type=peer_type,
                    username=username,
                    phone_number=phone_number,
                    last_update_on=s,
                )
                await new_peer.insert()

    async def update_usernames(self, usernames: List[Tuple[int, str]]):
        """
        Update usernames using a list of tuples: (peer_id, username)
        """
        s = int(time.time())
        for peer_id, username in usernames:
            # Remove any existing username documents with the same peer_id
            await UsernameDoc.find(UsernameDoc.peer_id == peer_id).delete()
            doc = await UsernameDoc.find_one(UsernameDoc._id == username)
            if doc:
                doc.peer_id = peer_id
                doc.last_update_on = s
                await doc.save()
            else:
                new_username = UsernameDoc(
                    _id=username, peer_id=peer_id, last_update_on=s
                )
                await new_username.insert()

    async def update_state(self, value: Any = object):
        """
        Update or retrieve the update state.

        - If called with no argument (value == object), return a list of state values.
        - If value is an int, delete the state document with that _id.
        - If value is a tuple (id, pts, qts, date, seq), upsert the state document.
        """
        if value == object:
            states = []
            async for state in UpdateStateDoc.find_all():
                states.append([state._id, state.pts, state.qts, state.date, state.seq])
            return states if states else None
        else:
            if isinstance(value, int):
                doc = await UpdateStateDoc.find_one(UpdateStateDoc._id == value)
                if doc:
                    await doc.delete()
            else:
                state_id, pts, qts, date_val, seq = value
                doc = await UpdateStateDoc.find_one(UpdateStateDoc._id == state_id)
                if doc:
                    doc.pts = pts
                    doc.qts = qts
                    doc.date = date_val
                    doc.seq = seq
                    await doc.save()
                else:
                    new_state = UpdateStateDoc(
                        _id=state_id, pts=pts, qts=qts, date=date_val, seq=seq
                    )
                    await new_state.insert()

    async def remove_state(self, chat_id: int):
        """
        Remove the update state document for the given chat_id.
        """
        doc = await UpdateStateDoc.find_one(UpdateStateDoc._id == chat_id)
        if doc:
            await doc.delete()

    async def get_peer_by_id(self, peer_id: int):
        """
        Retrieve a peer by its ID and return a Pyrogram input peer.
        """
        doc = await PeerDoc.find_one(PeerDoc._id == peer_id)
        if not doc:
            raise KeyError(f"ID not found: {peer_id}")
        return get_input_peer(doc._id, doc.access_hash, doc.type)

    async def get_peer_by_username(self, username: str):
        """
        Retrieve a peer using its username.
        """
        doc = await PeerDoc.find_one(PeerDoc.username == username)
        if doc is None:
            doc = await UsernameDoc.find_one(UsernameDoc._id == username)
            if doc is None:
                raise KeyError(f"Username not found: {username}")
            if abs(time.time() - doc.last_update_on) > self.USERNAME_TTL:
                raise KeyError(f"Username expired: {username}")
            doc = await PeerDoc.find_one(PeerDoc._id == doc.peer_id)
            if doc is None:
                raise KeyError(f"Username not found: {username}")
        if abs(time.time() - doc.last_update_on) > self.USERNAME_TTL:
            raise KeyError(f"Username expired: {username}")
        return get_input_peer(doc._id, doc.access_hash, doc.type)

    async def get_peer_by_phone_number(self, phone_number: str):
        """
        Retrieve a peer using its phone number.
        """
        doc = await PeerDoc.find_one(PeerDoc.phone_number == phone_number)
        if doc is None:
            raise KeyError(f"Phone number not found: {phone_number}")
        return get_input_peer(doc._id, doc.access_hash, doc.type)

    async def _get(self):
        """
        Internal helper: retrieve a session attribute based on the caller's function name.
        """
        attr = inspect.stack()[2].function
        session = await SessionDoc.find_one(SessionDoc._id == 0)
        if not session:
            return None
        return getattr(session, attr, None)

    async def _set(self, value: Any):
        """
        Internal helper: update a session attribute based on the caller's function name.
        """
        attr = inspect.stack()[2].function
        session = await SessionDoc.find_one(SessionDoc._id == 0)
        if session:
            setattr(session, attr, value)
            await session.save()

    async def _accessor(self, value: Any = object):
        return await self._get() if value == object else await self._set(value)

    async def dc_id(self, value: int = object):
        return await self._accessor(value)

    async def api_id(self, value: int = object):
        return await self._accessor(value)

    async def test_mode(self, value: bool = object):
        return await self._accessor(value)

    async def auth_key(self, value: bytes = object):
        return await self._accessor(value)

    async def date(self, value: int = object):
        return await self._accessor(value)

    async def user_id(self, value: int = object):
        return await self._accessor(value)

    async def is_bot(self, value: bool = object):
        return await self._accessor(value)
