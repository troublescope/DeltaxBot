from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String

from .database_provider import Base


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=True)
    user_id = Column(BigInteger, nullable=True)
    chat_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Music(Base):
    __tablename__ = "musics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
