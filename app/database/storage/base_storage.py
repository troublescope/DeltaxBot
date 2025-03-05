from beanie import Document
from pydantic import Field


class SessionDoc(Document):
    _id: int = Field(default=0, alias="_id")
    dc_id: int
    api_id: Optional[int] = None
    test_mode: Optional[int] = None
    auth_key: bytes
    date: int
    user_id: int
    is_bot: int

    class Settings:
        name = "session"


class PeerDoc(Document):
    _id: int = Field(alias="_id")
    access_hash: int
    type: str
    username: Optional[str] = None
    phone_number: Optional[str] = None
    last_update_on: int

    class Settings:
        name = "peers"


class UsernameDoc(Document):
    _id: str = Field(alias="_id")
    peer_id: int
    last_update_on: int

    class Settings:
        name = "usernames"


class UpdateStateDoc(Document):
    _id: int = Field(alias="_id")
    pts: int
    qts: int
    date: int
    seq: int

    class Settings:
        name = "update_state"
