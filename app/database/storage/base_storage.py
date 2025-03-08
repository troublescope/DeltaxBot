from typing import Optional

from beanie import Document
from pydantic import Field


class SessionDoc(Document):
    id: int = Field(default=0, alias="_id")
    dc_id: int
    api_id: Optional[int] = None
    test_mode: Optional[int] = None
    auth_key: bytes
    date: int
    user_id: Optional[int] = Field(default=0)
    is_bot: Optional[bool] = Field(default=False)

    class Settings:
        name = "session"


class PeerDoc(Document):
    id: int = Field(alias="_id")
    access_hash: int
    type: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    last_update_on: int

    class Settings:
        name = "peers"


class UsernameDoc(Document):
    id: str = Field(alias="_id")
    peer_id: int
    last_update_on: int

    class Settings:
        name = "usernames"


class UpdateStateDoc(Document):
    id: int = Field(alias="_id")
    pts: int
    qts: Optional[int]
    date: int
    seq: Optional[int]

    class Settings:
        name = "update_state"
